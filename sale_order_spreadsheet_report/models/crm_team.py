from odoo import models, fields

class CrmTeam(models.Model):
    _inherit = "crm.team"

    sale_spreadsheet_template_id = fields.Many2one(
        "sale.order.report.spreadsheet.template",
        string="Sale Spreadsheet Template",
        help="Default spreadsheet template for sale orders of this sales team."
    )
