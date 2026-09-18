from odoo import _, api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    variance_revaluation_ids = fields.One2many(
        "stock.value.revaluation", "source_move_id", string="Late Revaluations")
    variance_revaluation_count = fields.Integer(compute="_compute_variance_revaluation_count")

    @api.depends("variance_revaluation_ids")
    def _compute_variance_revaluation_count(self):
        for move in self:
            move.variance_revaluation_count = len(move.variance_revaluation_ids)

    def _post(self, soft=True):
        """Run the late revaluation engine around vendor documents; reverse adjustments on credit notes.

        Posting a vendor bill or credit note re-runs ``_set_value`` on the incoming moves it pays for
        (stock_account/models/account_move.py:42, same selection as ``_variance_vendor_moves``), which is
        how another price, another exchange rate or a subcontractor bill rewrites a receipt already done.
        The values have to be read around ``super()``: there is no other record of what they were.
        """
        if self.env.context.get("variance_skip_engine"):
            return super()._post(soft=soft)
        Revaluation = self.env["stock.value.revaluation"]
        vendor_docs = self.filtered(lambda m: m.move_type in ("in_invoice", "in_refund"))
        watched = {}
        for doc in vendor_docs:
            moves = doc._variance_vendor_moves()
            if not moves:
                continue
            products = {}
            for product in moves.product_id.filtered("is_storable"):
                products[product] = Revaluation._variance_snapshot(product, doc.company_id)
            watched[doc] = ({m.id: m.value for m in moves}, products)

        posted = super()._post(soft=soft)

        for doc, (values, products) in watched.items():
            if doc not in posted:
                continue
            moves = self.env["stock.move"].browse(list(values))
            moves.invalidate_recordset(["value"])
            for product, before in products.items():
                product_moves = moves.filtered(lambda m, p=product: m.product_id == p)
                entry_deltas = {m: m.value - values[m.id] for m in product_moves
                                if not doc.company_id.currency_id.is_zero(m.value - values[m.id])}
                revaluation = sum(entry_deltas.values())
                if doc.company_id.currency_id.is_zero(revaluation):
                    continue
                # The bill line itself carries the revaluation into stock valuation (real time): what Odoo
                # posted for the revaluation IS the revaluation.
                Revaluation._variance_handle_event(
                    product, doc.company_id, before, doc.date, "vendor_bill", revaluation,
                    native_amount=revaluation, entry_deltas=entry_deltas, source_move_id=doc.id)

        for refund in posted.filtered(lambda m: m.move_type == "out_refund"):
            Revaluation._variance_reverse_for_refund(refund)
        return posted

    def _variance_vendor_moves(self):
        """Incoming moves already done that the core re-values when this document posts."""
        self.ensure_one()
        return self.line_ids._get_stock_moves().filtered(
            lambda m: m.state == "done" and (m.is_in or m.is_dropship))

    def action_view_variance_revaluations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window", "name": _("Late Revaluations"),
            "res_model": "stock.value.revaluation", "view_mode": "list,form",
            "domain": ["|", ("source_move_id", "=", self.id), ("parent_id.source_move_id", "=", self.id)],
        }
