# -*- coding: utf-8 -*-
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.tests import tagged
from odoo.exceptions import ValidationError

@tagged('post_install', '-at_install')
class TestExpenseInvoiceAutomation(TestExpenseCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Ensure company is set up for automation
        cls.env.company.autocreate_invoice_from_expense = True
        
        # Vendor with AP account
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Test Vendor AP',
            'property_account_payable_id': cls.company_data['default_account_payable'].id,
        })
        
        cls.tax_0 = cls.env['account.tax'].create({
            'name': 'Tax 0%',
            'amount_type': 'percent',
            'amount': 0,
            'type_tax_use': 'purchase',
        })
        
        cls.expense_product = cls.env['product.product'].create({
            'name': 'Test Expense Product',
            'type': 'consu',
            'can_be_expensed': True,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
            'standard_price': 100.0,
            'supplier_taxes_id': [(6, 0, cls.tax_0.ids)],
        })

    def test_01_company_account_flow(self):
        """ Test that a company_account expense creates a Vendor Bill and payment is reconciled """
        expense = self.env['hr.expense'].create({
            'name': 'Company Expense 1',
            'employee_id': self.expense_employee.id,
            'product_id': self.expense_product.id,
            'tax_ids': [(6, 0, self.tax_0.ids)],
            'total_amount': 100.0,
            'payment_mode': 'company_account',
            'vendor_id': self.vendor.id,
        })
        expense.action_submit()
        expense.action_approve()
        expense.action_post()
        
        # Check Vendor Bill
        self.assertEqual(expense.vendor_bill_count, 1)
        bill = self.env['account.move'].search([('expense_to_invoice_origin_ids', 'in', expense.id)])
        self.assertEqual(bill.state, 'posted')
        self.assertEqual(bill.partner_id, self.vendor)
        self.assertEqual(bill.amount_total, 100.0)
        self.assertEqual(bill.payment_state, 'paid', "Bill should be paid by the auto-generated payment move")
        
    def test_02_own_account_flow(self):
        """ Test that an own_account expense creates a Vendor Bill and receipt is reconciled against AP """
        expense = self.env['hr.expense'].create({
            'name': 'Own Expense 1',
            'employee_id': self.expense_employee.id,
            'product_id': self.expense_product.id,
            'tax_ids': [(6, 0, self.tax_0.ids)],
            'total_amount': 150.0,
            'payment_mode': 'own_account',
            'vendor_id': self.vendor.id,
        })
        
        expense.action_submit()
        expense.action_approve()
        
        action = expense.action_post()
        wizard = self.env['hr.expense.post.wizard'].with_context(action.get('context')).browse(action['res_id'])
        wizard.action_post_entry()
        
        self.assertEqual(expense.vendor_bill_count, 1)
        bill = self.env['account.move'].search([('expense_to_invoice_origin_ids', 'in', expense.id)])
        self.assertEqual(bill.state, 'posted')
        self.assertEqual(bill.partner_id, self.vendor)
        self.assertEqual(bill.amount_total, 150.0)
        self.assertEqual(bill.payment_state, 'paid')

    def test_03_force_vendor(self):
        self.env.company.force_vendor_on_expense = True
        with self.assertRaises(ValidationError):
            self.env['hr.expense'].create({
                'name': 'No Vendor Expense',
                'employee_id': self.expense_employee.id,
                'product_id': self.expense_product.id,
                'total_amount': 200.0,
                'payment_mode': 'company_account',
            })

    def test_04_split_expense_grouping(self):
        """ Divide un gasto en dos, los aprueba y postea. Verifica que generan una sola factura """
        origin_expense = self.env['hr.expense'].create({
            'name': 'Origin Expense',
            'employee_id': self.expense_employee.id,
            'product_id': self.expense_product.id,
            'tax_ids': [(6, 0, self.tax_0.ids)],
            'total_amount': 300.0,
            'payment_mode': 'company_account',
            'vendor_id': self.vendor.id,
        })

        split_wizard = self.env['hr.expense.split.wizard'].with_context(active_ids=[origin_expense.id]).create({
            'expense_id': origin_expense.id,
        })
        # Mock split values to simulate the UI
        split_wizard.expense_split_line_ids.unlink()
        self.env['hr.expense.split'].create([
            {
                'wizard_id': split_wizard.id,
                'name': 'Split 1',
                'product_id': self.expense_product.id,
                'employee_id': origin_expense.employee_id.id,
                'total_amount_currency': 100.0,
                'expense_id': origin_expense.id,
            },
            {
                'wizard_id': split_wizard.id,
                'name': 'Split 2',
                'product_id': self.expense_product.id,
                'employee_id': origin_expense.employee_id.id,
                'total_amount_currency': 200.0,
                'expense_id': origin_expense.id,
            }
        ])
        split_wizard.action_split_expense()

        # Retrieve the generated expenses
        expenses = self.env['hr.expense'].search([('split_expense_origin_id', '=', origin_expense.id)])
        self.assertEqual(len(expenses), 2)
        
        expenses.action_submit()
        expenses.action_approve()
        expenses.action_post()
            
        bills = self.env['account.move'].search([('expense_to_invoice_origin_ids', 'in', expenses.ids)])
        self.assertEqual(len(bills), 1, "Should create exactly ONE vendor bill for the grouped split expenses")
        self.assertEqual(len(bills.invoice_line_ids), 2, "Vendor bill should have 2 lines for the splits")
        self.assertEqual(bills.amount_total, 300.0)
