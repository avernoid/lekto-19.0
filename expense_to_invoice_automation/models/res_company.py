# -*- coding: utf-8 -*-
from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    autocreate_invoice_from_expense = fields.Boolean(
        string="Autocreate Invoices from Expenses",
        default=False,
        help="If enabled, posting HR Expenses will automatically create Vendor Bills (in_invoice) instead of generic journal entries or receipts. This ensures proper Accounts Payable reconciliation."
    )
    force_vendor_on_expense = fields.Boolean(
        string="Force Vendor on Expenses",
        default=False,
        help="If enabled, the Vendor (Partner) field becomes strictly required on all expenses regardless of the payment mode, ensuring that every expense can generate a valid Accounts Payable Vendor Bill."
    )
    expense_vendor_bill_journal_id = fields.Many2one(
        'account.journal',
        string="Vendor Bill Journal",
        domain="[('type', '=', 'purchase')]",
        help="Optional. Select a dedicated Purchase journal for the Vendor Bills created automatically from expenses. If left empty, Odoo's default Purchase journal will be used (which might require Document Types if LatAm is installed)."
    )
