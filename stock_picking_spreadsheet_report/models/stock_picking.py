from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = "stock.picking"

    spreadsheet_ids = fields.One2many(
        "stock.picking.spreadsheet",
        "picking_id",
        string="Spreadsheets",
    )
    spreadsheet_count = fields.Integer(compute="_compute_spreadsheet_count")

    @api.depends("spreadsheet_ids")
    def _compute_spreadsheet_count(self):
        for picking in self:
            picking.spreadsheet_count = len(picking.spreadsheet_ids)

    def action_open_spreadsheet_report(self):
        self.ensure_one()
        
        # 1. If report exists, open it
        if self.spreadsheet_ids:
            return self.spreadsheet_ids[0].action_open_spreadsheet()

        # 2. Find Template (Partner > Picking Type)
        template = self.partner_id.picking_spreadsheet_template_id or self.picking_type_id.spreadsheet_template_id

        if not template:
            raise UserError(_(
                "No Spreadsheet Template found!\n\n"
                "Please configure a template in:\n"
                "1. The Partner (Contact form)\n"
                "2. Or the Picking Type (Operation Type configuration)"
            ))

        if not template.spreadsheet_id:
             raise UserError(_("The configured template has no linked spreadsheet."))

        # 3. Create Report from Template
        new_spreadsheet = template.spreadsheet_id.copy({
            "picking_id": self.id,
            "name": f"{template.name} - {self.name}",
        })

        return new_spreadsheet.action_open_spreadsheet()
