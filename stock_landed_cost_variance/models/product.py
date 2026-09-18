from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _variance_value_known_at(self, date_end):
        """(quantity, value) of the product as it was known at the end of ``date_end`` (design v4, D7).

        Stored values of the moves done up to that date, minus every revaluation whose event came
        later -- native landed costs by their date, amounts folded by this module by their event date --
        plus the live rows (value dropped by the engine) known at that date.

        This is what a period report must print so that a period already filed regenerates identically
        and closes exactly where the next one opens (measured byte-identical on the PLE 13.1).
        """
        self.ensure_one()
        company = self.env.company
        end = fields.Datetime.to_datetime(date_end).replace(hour=23, minute=59, second=59)
        moves = self.env["stock.move"].sudo().search([
            ("product_id", "=", self.id), ("company_id", "=", company.id), ("state", "=", "done"),
            ("date", "<=", end), "|", ("is_in", "=", True), ("is_out", "=", True)])
        stored = sum(m.value if m.is_in else -m.value for m in moves)
        qty = sum(m._get_valued_qty() if m.is_in else -m._get_valued_qty() for m in moves)
        Variance = self.env["stock.value.variance"].sudo()
        folded_later = Variance.search([
            ("move_id", "in", moves.ids), ("absorbed", "=", True), ("kind", "not in", ("legacy",)),
            ("date", ">", end)])
        live_known = Variance.search([
            ("move_id", "in", moves.ids), ("absorbed", "=", False), ("kind", "not in", ("legacy",)),
            ("date", "<=", end)])
        landed_later = self.env["stock.valuation.adjustment.lines"].sudo().search([
            ("move_id", "in", moves.ids), ("cost_id.state", "=", "done"), ("cost_id.date", ">", date_end)])
        value = stored - sum(folded_later.mapped("ledger_amount")) \
            - sum(landed_later.mapped("additional_landed_cost")) + sum(live_known.mapped("ledger_amount"))
        return qty, value

    def _variance_events_in_period(self, date_from, date_to):
        """Late revaluation amounts dated inside a period that belong to moves done BEFORE it.

        Returned as (move, dict) sorted by date; used by period reports to print them in the period of
        the event, with the event date (design v4, D7).
        """
        self.ensure_one()
        start = fields.Datetime.to_datetime(date_from)
        end = fields.Datetime.to_datetime(date_to).replace(hour=23, minute=59, second=59)
        events = []
        for adj in self.env["stock.valuation.adjustment.lines"].sudo().search([
                ("product_id", "=", self.id), ("cost_id.state", "=", "done"),
                ("cost_id.date", ">=", date_from), ("cost_id.date", "<=", date_to), ("move_id.date", "<", start)]):
            events.append((adj.move_id, {"cuo": f"{adj.id}LC", "value": adj.additional_landed_cost,
                                         "kind": "landed_cost", "date": adj.cost_id.date,
                                         "reference": adj.cost_id.name}))
        for row in self.env["stock.value.variance"].sudo().search([
                ("product_id", "=", self.id), ("kind", "not in", ("legacy",)),
                ("date", ">=", start), ("date", "<=", end), ("move_id.date", "<", start)]):
            events.append((row.move_id, {"cuo": f"{row.id}EV", "value": row.ledger_amount, "kind": row.kind,
                                         "date": row.date.date(),
                                         "reference": row.revaluation_id.name or row.move_id.reference}))
        return sorted(events, key=lambda e: (e[1]["date"], e[1]["cuo"]))
