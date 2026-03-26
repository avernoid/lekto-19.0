# -*- coding: utf-8 -*-
from odoo import api, fields, models

class AccountMove(models.Model):
    _inherit = 'account.move'

    expense_to_invoice_origin_ids = fields.Many2many(
        comodel_name='hr.expense',
        relation='account_move_hr_expense_to_invoice_rel',
        column1='move_id',
        column2='expense_id',
        string="Origin Expenses",
        help="Links this Vendor Bill back to the original HR Expenses that generated it through the Expense to Invoice Automation module.",
        copy=False,
    )
    
    expense_vendor_bill_count = fields.Integer(
        string='Expense Vendor Bills Count',
        compute='_compute_expense_vendor_bill_count'
    )

    def _compute_expense_vendor_bill_count(self):
        for move in self:
            if move.expense_ids:
                bills = self.env['account.move'].search([
                    ('expense_to_invoice_origin_ids', 'in', move.expense_ids.ids)
                ])
                move.expense_vendor_bill_count = len(bills)
            else:
                move.expense_vendor_bill_count = 0

    def action_open_expense_vendor_bills(self):
        self.ensure_one()
        bills = self.env['account.move'].search([
            ('expense_to_invoice_origin_ids', 'in', self.expense_ids.ids)
        ])
        
        result = self.env['ir.actions.act_window']._for_xml_id('account.action_move_in_invoice_type')
        if len(bills) == 1:
            result['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            result['res_id'] = bills.id
            # Also ensure the default type forces it to look like a bill
            result['context'] = {'default_move_type': 'in_invoice'}
        else:
            result['domain'] = [('id', 'in', bills.ids)]
            result['context'] = {'default_move_type': 'in_invoice'}
        return result

    @api.depends(
        'expense_ids',
        'line_ids.reconciled',
        'line_ids.amount_residual',
        'line_ids.balance',
    )
    def _compute_payment_state(self):
        super()._compute_payment_state()
        for move in self:
            if move.move_type == 'entry' and move.expense_ids:
                ap_lines = move.line_ids.filtered(lambda l: l.account_type == 'liability_payable')
                if not ap_lines:
                    move.payment_state = 'not_paid'
                    continue
                
                if all(l.reconciled for l in ap_lines):
                    move.payment_state = 'paid'
                elif any(l.amount_residual != l.balance for l in ap_lines):
                    move.payment_state = 'partial'
                else:
                    move.payment_state = 'not_paid'
