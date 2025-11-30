from odoo import models, fields

class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    spreadsheet_template_id = fields.Many2one(
        "stock.picking.spreadsheet.template",
        string="Spreadsheet Template",
        help="Default spreadsheet template for pickings of this type."
    )
