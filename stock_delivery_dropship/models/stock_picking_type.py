from odoo import api, fields, models


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    propagate_sale_carrier = fields.Boolean(
        string='Use Sale Order Carrier',
        help='Dropships of this operation type get the shipping method of the sale order when the '
             'purchase creates them, as deliveries from the warehouse already do. It can still be '
             'changed on the transfer before validating. Unchecked: standard Odoo behaviour (the '
             'dropship is created without shipping method).',
    )

    @api.model
    def _setup_dropship_shipping(self, print_label=True, propagate_sale_carrier=True):
        """Configure the Dropship operation types of every company at once (setup scripts and
        demo data): print labels on validation and take the carrier of the sale order."""
        dropship_types = self.sudo().with_context(active_test=False).search([('code', '=', 'dropship')])
        dropship_types.write({'print_label': print_label, 'propagate_sale_carrier': propagate_sale_carrier})
        return dropship_types.ids
