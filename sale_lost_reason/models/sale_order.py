from odoo import fields, models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    lost_reason_id = fields.Many2one('sale.lost.reason', string='Lost Reason', index=True, ondelete='restrict')

    def action_cancel(self):
        if self.env.context.get('disable_lost_reason_check'):
            return super().action_cancel()

        for order in self:
            if order.team_id.use_lost_reason and not order.lost_reason_id:
                return {
                    'name': 'Select Lost Reason',
                    'type': 'ir.actions.act_window',
                    'res_model': 'sale.lost.reason.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {'active_id': order.id},
                }
        
        return super().action_cancel()
