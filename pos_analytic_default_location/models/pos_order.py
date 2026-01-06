from odoo import models

class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _generate_pos_order_invoice(self):
        """ Inject pos_config_id into context during invoice generation. """
        self = self.with_context(pos_config_id=self.config_id.id)
        return super()._generate_pos_order_invoice()
