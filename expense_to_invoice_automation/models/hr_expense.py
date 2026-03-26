# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)

class HrExpense(models.Model):
    _inherit = 'hr.expense'

    reference = fields.Char(
        string="Reference",
        help="Reference of the Vendor Bill. This value will be mapped directly to the 'Bill Reference' field on the generated Vendor Bill.",
    )
    
    vendor_bill_count = fields.Integer(
        string="Vendor Bills Count",
        compute='_compute_vendor_bill_count',
    )

    def _compute_vendor_bill_count(self):
        for expense in self:
            expense.vendor_bill_count = self.env['account.move'].search_count([('expense_to_invoice_origin_ids', 'in', expense.id)])

    def action_open_vendor_bills(self):
        self.ensure_one()
        bills = self.env['account.move'].search([('expense_to_invoice_origin_ids', 'in', self.id)])
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_in_invoice_type")
        if len(bills) == 1:
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = bills.id
        else:
            action['domain'] = [('id', 'in', bills.ids)]
        return action

    @api.constrains('vendor_id', 'company_id')
    def _check_vendor_id_required(self):
        for expense in self:
            if expense.company_id.force_vendor_on_expense and not expense.vendor_id:
                raise ValidationError(_("The Vendor field is mandatory when invoice automation is enabled and configured to force its use."))

    def _create_company_paid_moves(self):
        automation_expenses = self.filtered(lambda e: e.company_id.autocreate_invoice_from_expense)
        if any(not e.vendor_id for e in automation_expenses):
            raise ValidationError(_("The Vendor field is mandatory to automate invoice creation."))

        if automation_expenses:
            automation_expenses._create_vendor_bills()

        moves = super(HrExpense, self)._create_company_paid_moves()

        company_account_expenses = self.filtered(lambda expense: expense.payment_mode == 'company_account')
        for expense, move in zip(company_account_expenses, moves):
            if not expense.company_id.autocreate_invoice_from_expense:
                continue
                
            bills = self.env['account.move'].search([('expense_to_invoice_origin_ids', 'in', expense.ids)])
            bill = bills.filtered(lambda b: expense.id in b.expense_to_invoice_origin_ids.ids)
            if not bill:
                continue
                
            bill_ap_line = bill.line_ids.filtered(lambda l: l.account_type == 'liability_payable' and l.partner_id == expense.vendor_id and not l.reconciled)
            if not bill_ap_line:
                continue
                
            payment_move_line = move.line_ids.filtered(lambda l: l.account_id == bill_ap_line.account_id and not l.reconciled)
            if payment_move_line:
                try:
                    (bill_ap_line + payment_move_line).reconcile()
                    _logger.info("Reconciled company_account payment move %s with bill %s", move.id, bill.id)
                except Exception as e:
                    _logger.error("Failed to reconcile company_account payment: %s", e)
                    
        return moves

    def action_post(self):
        return super(HrExpense, self).action_post()

    def _post_without_wizard(self):
        automation_expenses = self.filtered(lambda e: e.company_id.autocreate_invoice_from_expense)
        if any(not e.vendor_id for e in automation_expenses):
            raise ValidationError(_("The Vendor field is mandatory to automate invoice creation."))

        if automation_expenses:
            automation_expenses._create_vendor_bills()

        res = super(HrExpense, self)._post_without_wizard()

        if automation_expenses:
            own_account = automation_expenses.filtered(lambda e: e.payment_mode == 'own_account')
            if own_account:
                own_account._reconcile_with_vendor_bills()

        return res

    def _create_vendor_bills(self):
        """ Groups expenses and creates Vendor Bills (in_invoice) """
        moves_to_create = []
        # We group expenses by origin if split, otherwise by themselves, and by vendor/currency.
        def _get_group_key(expense):
            origin_id = expense.split_expense_origin_id.id if expense.split_expense_origin_id else expense.id
            return (expense.company_id.id, expense.vendor_id.id, expense.currency_id.id, origin_id)

        grouped_expenses = {}
        for expense in self:
            key = _get_group_key(expense)
            grouped_expenses.setdefault(key, self.env['hr.expense'])
            grouped_expenses[key] |= expense

        for key, expenses in grouped_expenses.items():
            company_id, vendor_id, currency_id, origin_id = key
            vendor = self.env['res.partner'].browse(vendor_id)
            
            # Use reference of the first expense if available
            ref = next((e.reference for e in expenses if e.reference), expenses[0].name)
            
            invoice_lines = []
            for e in expenses:
                line_vals = {
                    'name': e.name,
                    'product_id': e.product_id.id,
                    'quantity': e.quantity,
                    'price_unit': e.price_unit,
                    'account_id': e.account_id.id or e.product_id.property_account_expense_id.id or e.company_id.expense_account_id.id,
                    'tax_ids': [fields.Command.set(e.tax_ids.ids)],
                    'analytic_distribution': e.analytic_distribution,
                }
                invoice_lines.append(fields.Command.create(line_vals))

            move_vals = expenses._get_vendor_bill_vals(company_id, vendor, currency_id, ref, invoice_lines)
            moves_to_create.append(move_vals)

        if moves_to_create:
            invoices = self.env['account.move'].sudo().create(moves_to_create)
            # Post invoices to generate the AP entries to reconcile against
            invoices.action_post()

    def _get_vendor_bill_vals(self, company_id, vendor, currency_id, ref, invoice_lines):
        company = self.env['res.company'].browse(company_id)
        vals = {
            'move_type': 'in_invoice',
            'partner_id': vendor.id,
            'currency_id': currency_id,
            'invoice_date': self[0].date or fields.Date.context_today(self),
            'date': self[0].date or fields.Date.context_today(self),
            'company_id': company_id,
            'ref': ref,
            'invoice_line_ids': invoice_lines,
            'expense_to_invoice_origin_ids': [fields.Command.set(self.ids)],
        }
        if company.expense_vendor_bill_journal_id:
            vals['journal_id'] = company.expense_vendor_bill_journal_id.id
            
        return vals

    def _reconcile_with_vendor_bills(self):
        """ Reconciles the generated payment/receipt lines with the vendor bill AP lines """
        # Let's find the bills linked to these expenses
        bills = self.env['account.move'].search([('expense_to_invoice_origin_ids', 'in', self.ids)])
        
        for expense in self:
            bill = bills.filtered(lambda b: expense.id in b.expense_to_invoice_origin_ids.ids)
            if not bill:
                continue

            bill_ap_line = bill.line_ids.filtered(lambda l: l.account_type == 'liability_payable' and l.partner_id == expense.vendor_id)
            if not bill_ap_line:
                continue
                
            expense_move_line = self.env['account.move.line'].search([
                ('expense_id', '=', expense.id),
                ('account_id', '=', bill_ap_line.account_id.id),
                ('partner_id', '=', expense.vendor_id.id),
                ('reconciled', '=', False),
                ('move_id.move_type', '=', 'entry')
            ], limit=1)
            
            _logger.info("Searching own_account expense_move_line for expense %s: %s", expense.id, expense_move_line)
            if expense_move_line:
                _logger.info("Found expense_move_line: balance %s", expense_move_line.balance)
                _logger.info("Bill AP line: balance %s", bill_ap_line.balance)
                try:
                    (bill_ap_line + expense_move_line).reconcile()
                except Exception as e:
                    _logger.error("Failed to reconcile own_account: %s", e)

    def _prepare_payments_vals(self):
        """ Overridden to charge standard AP Vendor instead of Expense, avoiding duplication. """
        if not self.company_id.autocreate_invoice_from_expense:
            return super()._prepare_payments_vals()
            
        self.ensure_one()
        journal = self.journal_id
        payment_method_line = self.payment_method_line_id
        if not payment_method_line:
            raise UserError(_("You need to add a manual payment method on the journal (%s)", journal.name))
        
        ap_account = self.vendor_id.property_account_payable_id or self.vendor_id.parent_id.property_account_payable_id
        if not ap_account:
            raise UserError(_("No account payable found for vendor %s", self.vendor_id.name))

        move_lines = []
        # AP Line (Debit, since we are paying the vendor bill)
        move_lines.append({
            'name': self._get_move_line_name(),
            'account_id': ap_account.id,
            'balance': self.total_amount,
            'amount_currency': self.total_amount_currency,
            'currency_id': self.currency_id.id,
            'partner_id': self.vendor_id.id,
            'expense_id': self.id,
        })

        # Outstanding payment line (Credit)
        move_lines.append({
            'name': self._get_move_line_name(),
            'account_id': self._get_expense_account_destination(),
            'balance': -self.total_amount,
            'amount_currency': self.currency_id.round(-self.total_amount_currency),
            'currency_id': self.currency_id.id,
            'partner_id': self.vendor_id.id,
        })
        
        payment_vals = {
            'date': self.date,
            'memo': self.name,
            'journal_id': journal.id,
            'amount': self.total_amount_currency,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': self.vendor_id.id,
            'currency_id': self.currency_id.id,
            'payment_method_line_id': payment_method_line.id,
            'company_id': self.company_id.id,
        }
        move_vals = {
            **self._prepare_move_vals(),
            'date': self.date or fields.Date.context_today(self),
            'ref': self.name,
            'journal_id': journal.id,
            'partner_id': self.vendor_id.id,
            'currency_id': self.currency_id.id,
            'line_ids': [fields.Command.create(line) for line in move_lines],
            'attachment_ids': [
                fields.Command.create(attachment.copy_data({'res_model': 'account.move', 'res_id': False, 'raw': attachment.raw})[0])
                for attachment in self.attachment_ids]
        }
        return move_vals, payment_vals

    def _prepare_receipts_vals(self):
        """ Own account creates an in_receipt natively. To allow AP account in lines, we change it to 'entry' and add the employee payable line manually. """
        res_list = super(HrExpense, self)._prepare_receipts_vals()
        
        for res in res_list:
            is_automated = False
            for cmd in res.get('line_ids', []):
                if isinstance(cmd, (tuple, list)) and len(cmd) == 3 and cmd[0] == 0:
                    line_vals = cmd[2]
                    # Identify our line because we cleared taxes and we set account to an AP account
                    if 'tax_ids' in line_vals and not line_vals['tax_ids']:
                        # We should also verify it's a liability_payable account, but we assume the automation ran
                        is_automated = True
                        break
                        
            if is_automated:
                res['move_type'] = 'entry'
                total_amount = 0.0
                total_amount_currency = 0.0
                currency_id = res.get('currency_id')
                
                for cmd in res.get('line_ids', []):
                    if isinstance(cmd, (tuple, list)) and len(cmd) == 3 and cmd[0] == 0:
                        line_vals = cmd[2]
                        
                        amount = line_vals.get('price_unit', 0.0) * line_vals.get('quantity', 1.0)
                        line_vals['balance'] = amount
                        line_vals['amount_currency'] = amount
                        
                        total_amount += amount
                        total_amount_currency += amount
                
                employee_partner_id = res.get('commercial_partner_id') or res.get('partner_id')
                employee_partner = self.env['res.partner'].browse(employee_partner_id)
                emp_ap_account = employee_partner.property_account_payable_id
                
                if emp_ap_account:
                    res['line_ids'].append((0, 0, {
                        'name': res.get('ref', 'Employee Reimbursement'),
                        'account_id': emp_ap_account.id,
                        'balance': -total_amount,
                        'amount_currency': -total_amount_currency,
                        'currency_id': currency_id,
                        'partner_id': employee_partner_id,
                    }))
                
        return res_list

    def _prepare_move_lines_vals(self):
        """ Overridden to charge standard AP Vendor instead of Expense for own_account receipts """
        res = super()._prepare_move_lines_vals()
        if self.company_id.autocreate_invoice_from_expense:
            ap_account = self.vendor_id.property_account_payable_id or self.vendor_id.parent_id.property_account_payable_id
            if not ap_account:
                raise UserError(_("No account payable found for vendor %s", self.vendor_id.name))
            
            res['account_id'] = ap_account.id
            res['partner_id'] = self.vendor_id.id
            
            # Use gross amount because taxes are handled in the Vendor Bill
            res['quantity'] = 1
            res['price_unit'] = self.total_amount_currency if self.currency_id else self.total_amount
            res['tax_ids'] = []
            
        return res

