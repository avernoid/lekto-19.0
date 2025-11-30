from odoo import models, fields

class ProjectProject(models.Model):
    _inherit = "project.project"

    task_spreadsheet_template_id = fields.Many2one(
        "project.task.spreadsheet.template",
        string="Task Spreadsheet Template",
        help="Default spreadsheet template for tasks in this project."
    )
