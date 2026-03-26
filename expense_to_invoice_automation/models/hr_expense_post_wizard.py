# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.exceptions import ValidationError


class HrExpensePostWizard(models.TransientModel):
    _inherit = 'hr.expense.post.wizard'

    def action_post_entry(self):
        expenses = self.env['hr.expense'].browse(self.env.context.get('active_ids', []))
        # Filter own_account because company_account is already handled in _create_company_paid_moves
        automation_expenses = expenses.filtered(lambda e: e.company_id.autocreate_invoice_from_expense and e.payment_mode == 'own_account')
        
        if any(not e.vendor_id for e in automation_expenses):
            raise ValidationError(_("The Vendor field is mandatory to automate invoice creation."))

        if automation_expenses:
            automation_expenses._create_vendor_bills()

        res = super(HrExpensePostWizard, self).action_post_entry()

        if automation_expenses:
            automation_expenses._reconcile_with_vendor_bills()

        return res
