from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ResPartner(models.Model):
    _inherit = "res.partner"

    spreadsheet_ids = fields.One2many(
        "res.partner.spreadsheet",
        "partner_id",
        string="Spreadsheets",
    )
    spreadsheet_count = fields.Integer(compute="_compute_spreadsheet_count")
    
    # Priority 1: Direct assignment on Partner
    spreadsheet_template_id = fields.Many2one(
        "res.partner.spreadsheet.template",
        string="Spreadsheet Template",
        help="Default spreadsheet template for this contact."
    )

    @api.depends("spreadsheet_ids")
    def _compute_spreadsheet_count(self):
        for partner in self:
            partner.spreadsheet_count = len(partner.spreadsheet_ids)

    def action_open_spreadsheet_report(self):
        self.ensure_one()
        
        # 1. If report exists, open it
        if self.spreadsheet_ids:
            return self.spreadsheet_ids[0].action_open_spreadsheet()

        # 2. Find Template (Partner > Partner Tags)
        template = self.spreadsheet_template_id
        
        if not template and self.category_id:
            # Check tags for template (first tag with template wins)
            for tag in self.category_id:
                if tag.spreadsheet_template_id:
                    template = tag.spreadsheet_template_id
                    break

        if not template:
            raise UserError(_(
                "No Spreadsheet Template found!\n\n"
                "Please configure a template in:\n"
                "1. The Contact itself\n"
                "2. Or the Contact Tags"
            ))

        if not template.spreadsheet_id:
             raise UserError(_("The configured template has no linked spreadsheet."))

        # 3. Create Report from Template
        new_spreadsheet = template.spreadsheet_id.copy({
            "partner_id": self.id,
            "name": f"{template.name} - {self.name}",
        })

        return new_spreadsheet.action_open_spreadsheet()
