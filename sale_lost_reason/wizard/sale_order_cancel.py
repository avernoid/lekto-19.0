from odoo import fields, models

class SaleOrderCancel(models.TransientModel):
    _inherit = 'sale.order.cancel'

    lost_reason_id = fields.Many2one('sale.lost.reason', string='Lost Reason')
    use_lost_reason = fields.Boolean(related='order_id.team_id.use_lost_reason', string='Use Lost Reason')

    def action_cancel(self):
        res = super().action_cancel()
        if self.use_lost_reason and self.lost_reason_id:
            self.order_id.write({'lost_reason_id': self.lost_reason_id.id})
        return res
