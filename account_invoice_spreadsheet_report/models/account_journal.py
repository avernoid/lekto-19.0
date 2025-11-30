from odoo import models, fields

class AccountJournal(models.Model):
    _inherit = "account.journal"

    invoice_spreadsheet_template_id = fields.Many2one(
        "account.invoice.spreadsheet.template",
        string="Invoice Spreadsheet Template",
        help="Default spreadsheet template for invoices in this journal."
    )
