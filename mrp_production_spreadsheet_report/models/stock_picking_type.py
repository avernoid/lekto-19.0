from odoo import models, fields

class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    mrp_spreadsheet_template_id = fields.Many2one(
        "mrp.production.spreadsheet.template",
        string="MRP Spreadsheet Template",
        help="Default spreadsheet template for manufacturing orders of this operation type."
    )
