from odoo import models, fields

class SaleOrderTemplate(models.Model):
    _inherit = "sale.order.template"

    spreadsheet_template_id = fields.Many2one(
        "sale.order.report.spreadsheet.template",
        string="Spreadsheet Template",
        help="Default spreadsheet template for sale orders using this quotation template."
    )
