from odoo import models, fields

class ResPartner(models.Model):
    _inherit = "res.partner"

    picking_spreadsheet_template_id = fields.Many2one(
        "stock.picking.spreadsheet.template",
        string="Picking Spreadsheet Template",
        help="Default spreadsheet template for pickings related to this partner."
    )
