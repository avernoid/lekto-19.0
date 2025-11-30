from odoo import models, fields

class CrmTag(models.Model):
    _inherit = "crm.tag"

    sale_spreadsheet_template_id = fields.Many2one(
        "sale.order.report.spreadsheet.template",
        string="Sale Spreadsheet Template",
        help="Default spreadsheet template for sale orders with this tag."
    )
