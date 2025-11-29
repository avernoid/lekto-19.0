from odoo import models, fields

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    batch_spreadsheet_template_id = fields.Many2one(
        'stock.batch.spreadsheet.template', 
        string='Batch Spreadsheet Template',
        help='Default Spreadsheet Template used for Batch Pickings of this type.'
    )
