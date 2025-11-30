from odoo import models, fields, api, _
from odoo.exceptions import UserError

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    spreadsheet_ids = fields.One2many(
        "hr.employee.spreadsheet",
        "employee_id",
        string="Spreadsheets",
    )
    spreadsheet_count = fields.Integer(compute="_compute_spreadsheet_count")
    
    # Priority 1: Direct assignment on Employee
    spreadsheet_template_id = fields.Many2one(
        "hr.employee.spreadsheet.template",
        string="Spreadsheet Template",
        help="Default spreadsheet template for this employee."
    )

    @api.depends("spreadsheet_ids")
    def _compute_spreadsheet_count(self):
        for employee in self:
            employee.spreadsheet_count = len(employee.spreadsheet_ids)

    def action_open_spreadsheet_report(self):
        self.ensure_one()
        
        # 1. If report exists, open it
        if self.spreadsheet_ids:
            return self.spreadsheet_ids[0].action_open_spreadsheet()

        # 2. Find Template (Employee > Job Position)
        template = self.spreadsheet_template_id
        
        if not template and self.job_id:
            template = self.job_id.spreadsheet_template_id

        if not template:
            raise UserError(_(
                "No Spreadsheet Template found!\n\n"
                "Please configure a template in:\n"
                "1. The Employee itself\n"
                "2. Or the Job Position"
            ))

        if not template.spreadsheet_id:
             raise UserError(_("The configured template has no linked spreadsheet."))

        # 3. Create Report from Template
        new_spreadsheet = template.spreadsheet_id.copy({
            "employee_id": self.id,
            "name": f"{template.name} - {self.name}",
        })

        return new_spreadsheet.action_open_spreadsheet()
