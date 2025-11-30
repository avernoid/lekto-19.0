from odoo import models, fields

class MrpBom(models.Model):
    _inherit = "mrp.bom"

    spreadsheet_template_id = fields.Many2one(
        "mrp.production.spreadsheet.template",
        string="Spreadsheet Template",
        help="Default spreadsheet template for manufacturing orders using this bill of materials."
    )
