from odoo import models, fields

class ProjectTags(models.Model):
    _inherit = "project.tags"

    spreadsheet_template_id = fields.Many2one(
        "project.spreadsheet.template",
        string="Spreadsheet Template",
        help="Default spreadsheet template for projects with this tag."
    )
