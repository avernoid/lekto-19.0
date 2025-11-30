from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = "sale.order"

    spreadsheet_ids = fields.One2many(
        "sale.order.report.spreadsheet",
        "order_id",
        string="Spreadsheets",
    )
    spreadsheet_count = fields.Integer(compute="_compute_spreadsheet_count")

    @api.depends("spreadsheet_ids")
    def _compute_spreadsheet_count(self):
        for order in self:
            order.spreadsheet_count = len(order.spreadsheet_ids)

    def action_open_spreadsheet_report(self):
        self.ensure_one()
        
        # 1. If report exists, open it
        if self.spreadsheet_ids:
            return self.spreadsheet_ids[0].action_open_spreadsheet()

        # 2. Find Template (CRM Tags > Sales Team > Sale Order Template)
        template = None
        
        if self.tag_ids:
            # Check tags for template (first tag with template wins)
            for tag in self.tag_ids:
                if tag.sale_spreadsheet_template_id:
                    template = tag.sale_spreadsheet_template_id
                    break
        
        if not template and self.team_id:
            template = self.team_id.sale_spreadsheet_template_id
        
        if not template and self.sale_order_template_id:
            template = self.sale_order_template_id.spreadsheet_template_id

        if not template:
            raise UserError(_(
                "No Spreadsheet Template found!\n\n"
                "Please configure a template in:\n"
                "1. The CRM Tags\n"
                "2. The Sales Team\n"
                "3. Or the Sale Order Template (Quotation Template)"
            ))

        if not template.spreadsheet_id:
             raise UserError(_("The configured template has no linked spreadsheet."))

        # 3. Create Report from Template
        new_spreadsheet = template.spreadsheet_id.copy({
            "order_id": self.id,
            "name": f"{template.name} - {self.name}",
        })

        return new_spreadsheet.action_open_spreadsheet()
