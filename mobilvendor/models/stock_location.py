from odoo import models, fields

class StockLocation(models.Model):
    _inherit = 'stock.location'

    # Add the new field 'mobilvendor_sync'
    mobilvendor_sync = fields.Boolean(
        string="Mobilvendor SYNC",
        default=False,
        help="Sync stock locations to Mobilvendor"
    )
