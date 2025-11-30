from odoo import models, fields

class ResPartner(models.Model):
    _inherit = "res.partner"

    invoice_spreadsheet_template_id = fields.Many2one(
        "account.invoice.spreadsheet.template",
        string="Invoice Spreadsheet Template",
        help="Default spreadsheet template for invoices issued to this partner."
    )
