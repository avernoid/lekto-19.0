from odoo import models, fields

class ResPartnerCategory(models.Model):
    _inherit = "res.partner.category"

    spreadsheet_template_id = fields.Many2one(
        "res.partner.spreadsheet.template",
        string="Spreadsheet Template",
        help="Default spreadsheet template for contacts with this tag."
    )
