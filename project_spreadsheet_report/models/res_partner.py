from odoo import models, fields

class ResPartner(models.Model):
    _inherit = "res.partner"

    project_spreadsheet_template_id = fields.Many2one(
        "project.spreadsheet.template",
        string="Project Spreadsheet Template",
        help="Default spreadsheet template for projects related to this partner."
    )
