from odoo import fields, models

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    duplicate_product_policy = fields.Selection(
        selection=[
            ('allow', 'Allow'),
            ('warning', 'Warning'),
            ('block', 'Block'),
        ],
        string='Duplicate Product Policy',
        default='allow',
        help="Defines how to handle duplicate products (same product and description) in pickings."
    )
