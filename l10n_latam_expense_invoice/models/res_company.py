# -*- coding: utf-8 -*-
from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_latam_expense_allowed_document_type_ids = fields.Many2many(
        'l10n_latam.document.type',
        string="Allowed Document Types for Expenses",
        help="Select the document types that employees can choose when submitting expenses."
    )
    l10n_latam_expense_force_document_type = fields.Boolean(
        string="Force Document Type on Expenses",
        default=False,
        help="If enabled, the Document Type and Document Number become mandatory on all expenses, ensuring valid bills."
    )
    l10n_latam_expense_default_document_type_id = fields.Many2one(
        'l10n_latam.document.type',
        string="Default Document Type",
        help="Default document type to be used in expenses."
    )
