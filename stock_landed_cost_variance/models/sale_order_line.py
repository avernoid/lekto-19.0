from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _variance_costed_qty(self):
        """Quantity of this line whose cost of sales is posted: invoices minus credit notes.

        Read from the cost of sales lines themselves (``display_type = 'cogs'``, expense side),
        the same lines ``sale_stock`` uses for its cumulative formula.
        """
        self.ensure_one()
        invoices = self.order_id.invoice_ids.filtered(lambda m: m.state == "posted")
        lines = invoices.line_ids.filtered(
            lambda l: l.display_type == "cogs" and l.cogs_origin_id.sale_line_ids & self
            and l.account_id.account_type in ("expense", "expense_direct_cost"))
        return sum(lines.filtered(lambda l: l.move_id.move_type == "out_invoice").mapped("quantity")) \
            - sum(lines.filtered(lambda l: l.move_id.move_type == "out_refund").mapped("quantity"))
