# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        result = super()._post(soft=soft)
        customer_moves = self.filtered(
            lambda m: m.move_type in ('out_invoice', 'out_refund')
        )
        if customer_moves:
            # Flush all pending ORM writes to DB before searching in the trigger.
            # This ensures the state='posted' change from super()._post() is
            # visible to the account.move.line search in _compute_from_invoices().
            self.env.flush_all()
            customer_moves._recompute_seller_goals()
        return result

    def button_cancel(self):
        result = super().button_cancel()
        customer_moves = self.filtered(
            lambda m: m.move_type in ('out_invoice', 'out_refund')
        )
        if customer_moves:
            self.env.flush_all()
            customer_moves._recompute_seller_goals()
        return result

    def _recompute_seller_goals(self):
        """Recompute goal lines for the salespeople affected by these invoices.

        Only processes goals with source_type = 'invoice' to avoid
        triggering unnecessary queries on sale-order-based goals.
        ``invoice_user_id`` is the salesperson set on the invoice header.
        """
        salesperson_ids = self.mapped('invoice_user_id').ids
        if not salesperson_ids:
            return
        # Collect month/year periods affected by the invoices
        period_keys = set()
        for move in self:
            if move.invoice_date:
                period_keys.add((move.invoice_date.month, move.invoice_date.year))

        for month, year in period_keys:
            goals = self.env['sale.goal'].sudo().search([
                ('user_id', 'in', salesperson_ids),
                ('month', '=', month),
                ('year', '=', year),
                ('source_type', '=', 'invoice'),
            ])
            if goals:
                goals.mapped('line_ids')._compute_done()
                goals._recompute_global_done()
