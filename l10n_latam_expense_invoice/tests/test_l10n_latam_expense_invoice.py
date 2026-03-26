# -*- coding: utf-8 -*-
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.tests import tagged
from odoo.exceptions import ValidationError

@tagged('post_install', '-at_install')
class TestLatamExpenseInvoice(TestExpenseCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Ensure company is set up for automation
        cls.env.company.autocreate_invoice_from_expense = True
        
        # Vendor with AP account
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Test Vendor AP LatAm',
            'property_account_payable_id': cls.company_data['default_account_payable'].id,
        })
        
        cls.tax_0 = cls.env['account.tax'].create({
            'name': 'Tax 0%',
            'amount_type': 'percent',
            'amount': 0,
            'type_tax_use': 'purchase',
        })
        
        cls.expense_product = cls.env['product.product'].create({
            'name': 'Test LatAm Expense Product',
            'type': 'consu',
            'can_be_expensed': True,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
            'standard_price': 100.0,
            'supplier_taxes_id': [(6, 0, cls.tax_0.ids)],
        })

        # Document Type
        cls.document_type_factura = cls.env['l10n_latam.document.type'].create({
            'name': 'Factura',
            'doc_code_prefix': 'F',
            'code': '01',
            'report_name': 'Factura',
            'country_id': cls.env.company.country_id.id or cls.env.ref('base.pe').id,
        })

        cls.env.company.l10n_latam_expense_allowed_document_type_ids = [(4, cls.document_type_factura.id)]
        cls.env.company.l10n_latam_expense_default_document_type_id = cls.document_type_factura.id

    def test_01_latam_document_propagation(self):
        """ Test that LatAm document type and number propagate to Vendor Bill """
        expense = self.env['hr.expense'].create({
            'name': 'LatAm Expense 1',
            'employee_id': self.expense_employee.id,
            'product_id': self.expense_product.id,
            'tax_ids': [(6, 0, self.tax_0.ids)],
            'total_amount': 100.0,
            'payment_mode': 'company_account',
            'vendor_id': self.vendor.id,
            'l10n_latam_document_type_id': self.document_type_factura.id,
            'l10n_latam_document_number': 'F001-000123',
        })
        expense.action_submit()
        expense.action_approve()
        expense.action_post()
        
        # Check Vendor Bill
        self.assertEqual(expense.vendor_bill_count, 1)
        bill = self.env['account.move'].search([('expense_to_invoice_origin_ids', 'in', expense.id)])
        self.assertEqual(bill.state, 'posted')
        self.assertEqual(bill.partner_id, self.vendor)
        self.assertEqual(bill.l10n_latam_document_type_id.id, self.document_type_factura.id)
        self.assertEqual(bill.l10n_latam_document_number, 'F001-000123')

    def test_02_force_document_type(self):
        """ Test that force_document_type raises ValidationError if fields are missing """
        self.env.company.l10n_latam_expense_force_document_type = True
        
        with self.assertRaises(ValidationError):
            self.env['hr.expense'].create({
                'name': 'No Document Type Expense',
                'employee_id': self.expense_employee.id,
                'product_id': self.expense_product.id,
                'total_amount': 200.0,
                'payment_mode': 'company_account',
                'vendor_id': self.vendor.id,
                # Missing doc type and number
            })
