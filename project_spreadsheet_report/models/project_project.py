from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ProjectProject(models.Model):
    _inherit = "project.project"

    spreadsheet_ids = fields.One2many(
        "project.spreadsheet",
        "project_id",
        string="Spreadsheets",
    )
    spreadsheet_count = fields.Integer(compute="_compute_spreadsheet_count")

    @api.depends("spreadsheet_ids")
    def _compute_spreadsheet_count(self):
        for project in self:
            project.spreadsheet_count = len(project.spreadsheet_ids)

    def action_open_spreadsheet_report(self):
        self.ensure_one()
        
        # 1. If report exists, open it
        if self.spreadsheet_ids:
            return self.spreadsheet_ids[0].action_open_spreadsheet()

        # 2. Find Template (Partner > Project Tags)
        template = self.partner_id.project_spreadsheet_template_id
        
        if not template and self.tag_ids:
            # Check tags for template (first tag with template wins)
            for tag in self.tag_ids:
                if tag.spreadsheet_template_id:
                    template = tag.spreadsheet_template_id
                    break

        if not template:
            raise UserError(_(
                "No Spreadsheet Template found!\n\n"
                "Please configure a template in:\n"
                "1. The Partner (Contact form)\n"
                "2. Or the Project Tags (Project Tags configuration)"
            ))

        if not template.spreadsheet_id:
             raise UserError(_("The configured template has no linked spreadsheet."))

        # 3. Create Report from Template
        new_spreadsheet = template.spreadsheet_id.copy({
            "project_id": self.id,
            "name": f"{template.name} - {self.name}",
        })

        return new_spreadsheet.action_open_spreadsheet()
