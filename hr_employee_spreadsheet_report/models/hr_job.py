from odoo import models, fields

class HrJob(models.Model):
    _inherit = "hr.job"

    spreadsheet_template_id = fields.Many2one(
        "hr.employee.spreadsheet.template",
        string="Spreadsheet Template",
        help="Default spreadsheet template for employees with this job position."
    )
