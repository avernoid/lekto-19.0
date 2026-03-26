# -*- coding: utf-8 -*-
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    autocreate_invoice_from_expense = fields.Boolean(
        related='company_id.autocreate_invoice_from_expense',
        readonly=False
    )
    force_vendor_on_expense = fields.Boolean(
        related='company_id.force_vendor_on_expense',
        readonly=False
    )
    expense_vendor_bill_journal_id = fields.Many2one(
        related='company_id.expense_vendor_bill_journal_id',
        readonly=False
    )
