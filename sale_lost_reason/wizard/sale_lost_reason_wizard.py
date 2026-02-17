from odoo import fields, models, _

class SaleLostReasonWizard(models.TransientModel):
    _name = 'sale.lost.reason.wizard'
    _description = 'Sale Lost Reason Wizard'

    lost_reason_id = fields.Many2one('sale.lost.reason', string='Lost Reason', required=True)

    def action_confirm(self):
        self.ensure_one()
        active_id = self.env.context.get('active_id')
        if active_id:
            order = self.env['sale.order'].browse(active_id)
            order.write({'lost_reason_id': self.lost_reason_id.id})
            # Call the native cancel method but bypass the check we added in sale.order
            return order.with_context(disable_lost_reason_check=True).action_cancel()
