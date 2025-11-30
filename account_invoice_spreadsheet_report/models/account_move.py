from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = "account.move"

    spreadsheet_ids = fields.One2many(
        "account.invoice.spreadsheet",
        "invoice_id",
        string="Spreadsheets",
    )
    spreadsheet_count = fields.Integer(compute="_compute_spreadsheet_count")

    @api.depends("spreadsheet_ids")
    def _compute_spreadsheet_count(self):
        for move in self:
            move.spreadsheet_count = len(move.spreadsheet_ids)

    def action_open_spreadsheet_report(self):
        self.ensure_one()
        
        # 1. If report exists, open it
        if self.spreadsheet_ids:
            return self.spreadsheet_ids[0].action_open_spreadsheet()

        # 2. Find Template (Partner > Journal)
        template = self.partner_id.invoice_spreadsheet_template_id or self.journal_id.invoice_spreadsheet_template_id

        if not template:
            raise UserError(_(
                "No Spreadsheet Template found!\n\n"
                "Please configure a template in:\n"
                "1. The Customer (Partner form)\n"
                "2. Or the Journal (Journal configuration)"
            ))

        if not template.spreadsheet_id:
             raise UserError(_("The configured template has no linked spreadsheet."))

        # 3. Create Report from Template
        new_spreadsheet = template.spreadsheet_id.copy({
            "invoice_id": self.id,
            "name": f"{template.name} - {self.name}",
        })

        return new_spreadsheet.action_open_spreadsheet()
