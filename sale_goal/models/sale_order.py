# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        result = super().action_confirm()
        self._recompute_seller_goals()
        return result

    def action_cancel(self):
        result = super().action_cancel()
        self._recompute_seller_goals()
        return result

    def _recompute_seller_goals(self):
        """Recompute goal lines for the salespeople affected by these orders.

        Only processes goals with source_type = 'sale_order' to avoid
        triggering unnecessary queries on invoice-based goals.
        """
        salesperson_ids = self.mapped('user_id').ids
        if not salesperson_ids:
            return
        # Collect months/years affected by these orders
        period_keys = set()
        for order in self:
            if order.date_order:
                period_keys.add((order.date_order.month, order.date_order.year))

        for month, year in period_keys:
            goals = self.env['sale.goal'].sudo().search([
                ('user_id', 'in', salesperson_ids),
                ('month', '=', month),
                ('year', '=', year),
                ('source_type', '=', 'sale_order'),
            ])
            if goals:
                goals.mapped('line_ids')._compute_done()
                goals._recompute_global_done()
