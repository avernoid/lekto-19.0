from odoo import models, fields, api, _
from odoo.exceptions import UserError

class MrpProduction(models.Model):
    _inherit = "mrp.production"

    spreadsheet_ids = fields.One2many(
        "mrp.production.spreadsheet",
        "production_id",
        string="Spreadsheets",
    )
    spreadsheet_count = fields.Integer(compute="_compute_spreadsheet_count")

    @api.depends("spreadsheet_ids")
    def _compute_spreadsheet_count(self):
        for production in self:
            production.spreadsheet_count = len(production.spreadsheet_ids)

    def action_open_spreadsheet_report(self):
        self.ensure_one()
        
        # 1. If report exists, open it
        if self.spreadsheet_ids:
            return self.spreadsheet_ids[0].action_open_spreadsheet()

        # 2. Find Template (BoM > Picking Type)
        template = None
        
        if self.bom_id:
            template = self.bom_id.spreadsheet_template_id
        
        if not template and self.picking_type_id:
            template = self.picking_type_id.mrp_spreadsheet_template_id

        if not template:
            raise UserError(_(
                "No Spreadsheet Template found!\n\n"
                "Please configure a template in:\n"
                "1. The Bill of Materials\n"
                "2. Or the Picking Type (Operation Type configuration)"
            ))

        if not template.spreadsheet_id:
             raise UserError(_("The configured template has no linked spreadsheet."))

        # 3. Create Report from Template
        new_spreadsheet = template.spreadsheet_id.copy({
            "production_id": self.id,
            "name": f"{template.name} - {self.name}",
        })

        return new_spreadsheet.action_open_spreadsheet()
