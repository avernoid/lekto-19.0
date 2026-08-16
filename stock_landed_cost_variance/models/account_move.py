from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        """Record the part of a bill-driven revaluation that belongs to goods
        already gone.

        Posting a vendor bill re-runs ``_set_value`` on the receipts it pays
        for (``stock_account/models/account_move.py``), so a bill that differs
        from the purchase order silently rewrites the value of a movement that
        is already done -- measured: 2500 -> 2800.  The units delivered before
        that point stay recognised at the old cost, so the cost of sales is
        short and inventory is over by the same amount.

        The delta is taken around ``super()`` because there is no other way to
        know what the movement was worth before the bill moved it.
        """
        moves = self._variance_revalued_moves()
        before = {move.id: move.value for move in moves}

        posted = super()._post(soft=soft)

        if moves:
            moves.invalidate_recordset(["value"])
            posted._capture_bill_variance(before)
        return posted

    # ------------------------------------------------------------------
    def _variance_revalued_moves(self):
        """The moves the core will re-value on posting -- same selection it uses."""
        moves = self.line_ids._get_stock_moves()
        return moves.filtered(lambda m: m.is_in or m.is_dropship)

    def _capture_bill_variance(self, before):
        Variance = self.env["stock.value.variance"].sudo()
        vals_list = []
        for bill in self:
            company = bill.company_id
            currency = company.currency_id
            moves = bill._variance_revalued_moves()
            if not moves:
                continue

            remaining_by_product = {}
            for product in moves.product_id:
                remaining_by_product[product.id] = self.env["stock.move"]._variance_remaining_by_move(
                    product, company)

            for move in moves:
                base_amount = move.value - before.get(move.id, move.value)
                if currency.is_zero(base_amount):
                    continue
                if move._variance_has_manual_value():
                    continue
                valued_qty = move._get_valued_qty()
                if not valued_qty:
                    continue
                remaining = remaining_by_product.get(move.product_id.id, {}).get(move.id, 0.0)
                capitalized = currency.round(base_amount * remaining / valued_qty)
                low, high = sorted((0.0, base_amount))
                capitalized = min(max(capitalized, low), high)
                expensed = currency.round(base_amount - capitalized)
                vals_list.append({
                    "move_id": move.id,
                    "company_id": company.id,
                    "origin": "bill",
                    "account_move_id": bill.id,
                    "date": fields.Datetime.to_datetime(bill.date or bill.invoice_date),
                    "base_amount": base_amount,
                    "capitalized_amount": base_amount - expensed,
                    "expensed_amount": expensed,
                    "valued_qty": valued_qty,
                    "remaining_qty": remaining,
                    "ledger_amount": self.env["stock.value.variance"]._ledger_amount_for(
                        move, expensed),
                })
        return Variance.create(vals_list) if vals_list else Variance
