from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_posted_cogs_value(self):
        """Count late revaluation adjustments as cost of sales already posted (design v4, D5).

        ``sale_stock`` prices each new invoice's cost of sales as cumulative quantity x cost today minus
        the cost of sales already posted on the order line (sale_stock/models/account_move.py:165-185).
        Our adjustment for units already invoiced is cost of sales of that line; if the formula does not
        see it, the next invoice recovers the same amount again (measured: 650 instead of 550).
        """
        value = super()._get_posted_cogs_value()
        if self.sale_line_ids:
            adjustments = self.env["stock.cost.adjustment"].sudo().search([
                ("sale_line_id", "in", self.sale_line_ids.ids),
                ("revaluation_id.account_move_id.state", "=", "posted"),
            ])
            value += sum(adjustments.mapped("amount"))
        return value
