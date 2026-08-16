
from odoo import _, fields, models
from odoo.exceptions import UserError


class StockLandedCost(models.Model):
    _inherit = "stock.landed.cost"

    def button_validate(self):
        """Capture the split AFTER the core has done its work.

        Two reasons this cannot run before ``super()``:

        * ``button_validate`` itself creates the adjustment lines when the user
          validates without pressing Compute, so there would be nothing to read.
        * the core's own ``_set_value()`` at the end of each iteration does not
          move ``remaining_qty``: ``_run_fifo_get_stack`` is built from
          ``qty_available`` and ``_get_valued_qty()`` and never reads
          ``move.value``.  Reading afterwards yields the same ratio the core
          used for its journal entry.
        """
        res = super().button_validate()
        for cost in self:
            cost._capture_value_variance()
        return res

    def compute_landed_cost(self):
        """Refuse to wipe the adjustment lines of a validated cost.

        The core method is public, RPC-callable and has no state guard, and it
        opens with an unlink of every line of the cost.  Left alone it would
        strip the link between a posted reclassification entry and the rows
        that substantiate it.
        """
        done = self.filtered(lambda c: c.state == "done")
        if done:
            raise UserError(_(
                "Cannot recompute a validated landed cost (%s).",
                ", ".join(done.mapped("name")),
            ))
        return super().compute_landed_cost()

    # ------------------------------------------------------------------
    def _capture_value_variance(self):
        self.ensure_one()
        Variance = self.env["stock.value.variance"].sudo()
        company = self.company_id
        currency = company.currency_id

        lines = self.valuation_adjustment_lines.filtered(
            lambda line: line.move_id and line.additional_landed_cost)
        if not lines:
            return Variance

        # One FIFO stack rebuild per (company, product), never per line: each
        # rebuild runs paginated searches inside the validation transaction.
        remaining_by_product = {}
        for product in lines.move_id.product_id:
            remaining_by_product[product.id] = self.env["stock.move"]._variance_remaining_by_move(
                product, company)

        vals_list = []
        for line in lines:
            move = line.move_id
            if move.product_id.lot_valuated:
                vals_list += self._variance_vals_by_lot(line, company, currency)
                continue
            remaining = remaining_by_product.get(move.product_id.id, {}).get(move.id, 0.0)
            vals = self._variance_vals(line, move, company, currency, remaining)
            if vals:
                vals_list.append(vals)
        return Variance.create(vals_list) if vals_list else Variance

    def _variance_vals(self, line, move, company, currency, remaining, lot=None, base_amount=None):
        """Build one variance row.  Returns {} when there is nothing to record."""
        self.ensure_one()
        base_amount = line.additional_landed_cost if base_amount is None else base_amount
        if currency.is_zero(base_amount):
            return {}

        # A movement pinned by a manual product.value never received the landed
        # cost at all: _get_value_data sets add_extra_value = False as soon as
        # _get_manual_value returns a quantity.  Nothing to give back here --
        # but in perpetual the core still capitalised, so say so.
        if move._variance_has_manual_value():
            move._variance_log_manual_skip(self)
            return {}

        valued_qty = move._get_valued_qty(lot=lot) if lot else move._get_valued_qty()
        if not valued_qty:
            return {}

        capitalized = currency.round(base_amount * remaining / valued_qty)
        # Clamp to the base so a stack anomaly can never invert the split.
        low, high = sorted((0.0, base_amount))
        capitalized = min(max(capitalized, low), high)
        expensed = currency.round(base_amount - capitalized)

        return {
            "move_id": move.id,
            "company_id": company.id,
            "origin": "landed_cost",
            "landed_cost_line_id": line.id,
            # stock.landed.cost.date is a Date; the variance is a Datetime so it
            # orders alongside stock moves in a valued ledger.
            "date": fields.Datetime.to_datetime(self.date),
            "base_amount": base_amount,
            "capitalized_amount": base_amount - expensed,
            "expensed_amount": expensed,
            "valued_qty": valued_qty,
            "remaining_qty": remaining,
            "lot_id": lot.id if lot else False,
            "ledger_amount": self.env["stock.value.variance"]._ledger_amount_for(
                move, expensed),
        }

    def _variance_vals_by_lot(self, line, company, currency):
        """Split a lot-valuated movement per lot.

        Odoo 19 does prorate landed costs per lot -- through ``_set_value`` ->
        ``stock.lot._update_standard_price()`` -- it simply never exposes the
        split.  We rebuild it from the same FIFO stack, one per lot.
        """
        self.ensure_one()
        move = line.move_id
        vals_list = []
        total_qty = move._get_valued_qty()
        if not total_qty:
            return vals_list
        for lot in move.move_line_ids.lot_id:
            lot_qty = move._get_valued_qty(lot=lot)
            if not lot_qty:
                continue
            remaining = self.env["stock.move"]._variance_remaining_by_move(
                move.product_id, company, lot=lot).get(move.id, 0.0)
            share = currency.round(line.additional_landed_cost * lot_qty / total_qty)
            vals = self._variance_vals(
                line, move, company, currency, remaining, lot=lot, base_amount=share)
            if vals:
                vals_list.append(vals)
        # Rounding residue goes to the largest row so the rows still add up to
        # the cost line.
        if vals_list:
            residue = line.additional_landed_cost - sum(v["base_amount"] for v in vals_list)
            if not currency.is_zero(residue):
                biggest = max(vals_list, key=lambda v: abs(v["base_amount"]))
                biggest["base_amount"] += residue
                biggest["capitalized_amount"] += residue
                # expensed and therefore ledger_amount are untouched: the
                # residue lands entirely on the capitalised side.
        return vals_list
