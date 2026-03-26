# -*- coding: utf-8 -*-
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_latam_expense_allowed_document_type_ids = fields.Many2many(
        related='company_id.l10n_latam_expense_allowed_document_type_ids',
        readonly=False,
        help="Select the document types that employees are allowed to use when submitting expenses in this company. Only these types will be available in the expense form."
    )
    l10n_latam_expense_force_document_type = fields.Boolean(
        related='company_id.l10n_latam_expense_force_document_type',
        readonly=False,
        help="If enabled, it will be strictly required for employees to provide both a Document Type and a Document Number when creating an expense. Use this to enforce tax compliance."
    )
    l10n_latam_expense_default_document_type_id = fields.Many2one(
        related='company_id.l10n_latam_expense_default_document_type_id',
        readonly=False,
        help="Select the document type that will be automatically assigned to new expenses by default, saving time for employees during data entry."
    )
