from odoo import models, fields

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    show_reference_in_portal = fields.Boolean(
        string="Show Internal Reference in Portal",
        default=False,
        help="If enabled, the product's internal reference will be shown in the portal."
    )

    show_barcode_in_portal = fields.Boolean(
        string="Show Barcode in Portal",
        default=False,
        help="If enabled, the product's barcode will be shown in the portal."
    )
