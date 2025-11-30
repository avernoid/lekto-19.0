from odoo import models, fields

class ResPartner(models.Model):
    _inherit = "res.partner"

    task_spreadsheet_template_id = fields.Many2one(
        "project.task.spreadsheet.template",
        string="Task Spreadsheet Template",
        help="Default spreadsheet template for tasks related to this partner."
    )
