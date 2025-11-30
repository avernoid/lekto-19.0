from odoo import models, fields

class ProjectTags(models.Model):
    _inherit = "project.tags"

    task_spreadsheet_template_id = fields.Many2one(
        "project.task.spreadsheet.template",
        string="Task Spreadsheet Template",
        help="Default spreadsheet template for tasks with this tag."
    )
