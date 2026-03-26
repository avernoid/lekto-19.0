# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class HrExpense(models.Model):
    _inherit = 'hr.expense'

    l10n_latam_document_type_id = fields.Many2one(
        'l10n_latam.document.type',
        string='Document Type',
        default=lambda self: self.env.company.l10n_latam_expense_default_document_type_id,
        domain="[('id', 'in', allowed_document_type_ids)]",
        tracking=True,
        help="Select the Latin American document type for this expense. If configured, this document type will be automatically propagated to the generated vendor bill."
    )
    # Technical field to compute domain
    allowed_document_type_ids = fields.Many2many(
        related='company_id.l10n_latam_expense_allowed_document_type_ids'
    )
    
    l10n_latam_document_number = fields.Char(
        string='Document Number',
        tracking=True,
        help="Enter the physical or legal document number for this expense receipt. This number will be transferred to the vendor bill for tax reporting purposes."
    )

    @api.constrains('l10n_latam_document_type_id', 'l10n_latam_document_number', 'company_id')
    def _check_l10n_latam_document(self):
        for expense in self:
            if expense.company_id.l10n_latam_expense_force_document_type:
                if not expense.l10n_latam_document_type_id or not expense.l10n_latam_document_number:
                    raise ValidationError(_("The Document Type and Document Number fields are mandatory when LatAm invoice automation is configured to force their use."))

    def _get_vendor_bill_vals(self, company_id, vendor, currency_id, ref, invoice_lines):
        """ Inherit _get_vendor_bill_vals to inject l10n_latam fields into Vendor Bill """
        res = super(HrExpense, self)._get_vendor_bill_vals(company_id, vendor, currency_id, ref, invoice_lines)
        if self and self[0].l10n_latam_document_type_id:
            res['l10n_latam_document_type_id'] = self[0].l10n_latam_document_type_id.id
            # On Vendor Bills, l10n_latam_document_number maps to the physical number
            res['l10n_latam_document_number'] = self[0].l10n_latam_document_number
        return res
