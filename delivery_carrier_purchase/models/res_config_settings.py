from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    carrier_purchase = fields.Boolean(related='company_id.carrier_purchase', readonly=False)
    carrier_purchase_grouping = fields.Selection(related='company_id.carrier_purchase_grouping', readonly=False)
    carrier_purchase_auto_products = fields.Char(
        compute='_compute_carrier_purchase_auto_products',
        help='Delivery products that still create a purchase by themselves (Purchase Automatically).')

    @api.depends('carrier_purchase')
    def _compute_carrier_purchase_auto_products(self):
        products = self.env['delivery.carrier'].search([]).product_id.filtered('service_to_purchase')
        names = ', '.join(products.mapped('display_name'))
        for settings in self:
            settings.carrier_purchase_auto_products = names if settings.carrier_purchase else False
