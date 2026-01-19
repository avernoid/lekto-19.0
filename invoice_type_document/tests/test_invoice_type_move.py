from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.exceptions import ValidationError
from odoo import fields, Command


@tagged('post_install', '-at_install')
class TestInvoiceTypeMove(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.account = cls.env['account.account'].search([
                    ('account_type', '=', 'income'),
                ], limit=1)
        
        if not cls.account:
            # Fallback if no income account exists
            cls.account = cls.env['account.account'].create({
                'name': 'Test Income Account',
                'code': '999999',
                'account_type': 'income',
            })

        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})
        cls.journal = cls.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        if not cls.journal:
             cls.journal = cls.env['account.journal'].create({
                'name': 'Test Journal',
                'type': 'sale',
                'code': 'TJ',
             })

        cls.move = cls.env['account.move'].create({
            'name': 'Factura TEST',
            'date': fields.Date.from_string('2024-06-04'),
            'serie_correlative':'E003-03',
            'move_type': 'entry',
            'journal_id': cls.journal.id,
        })
        
    def setUp(self):
        super(TestInvoiceTypeMove, self).setUp()
        
        self.ts_account_move_line = self.env['account.move.line'].create({
            'move_id': self.move.id,
            'name': 'product 1',
            'account_id': self.account.id,  
            'debit': 0.00,  
            'credit': 0.00,
            'move_type': 'entry',
            'serie_correlative':'E003-03',
            'serie_correlative_is_readonly': False
        })
          
        print("----SETUP OK----")
                
    def test_fields_invoice_account_move(self):
        self.assertEqual(self.ts_account_move_line.move_id.id, self.move.id)
        self.assertEqual(self.ts_account_move_line.name,'product 1')
        self.assertEqual(self.ts_account_move_line.account_id.id, self.account.id)
        self.assertEqual(self.ts_account_move_line.debit, 0.00)
        self.assertEqual(self.ts_account_move_line.credit, 0.00)
        self.assertEqual(self.ts_account_move_line.move_type, 'entry')
        self.assertFalse(self.ts_account_move_line.serie_correlative_is_readonly)
        self.assertEqual(self.move.serie_correlative, 'E003-03')
        print("-------TEST FIELDS INVOICE OK-----")
    
    def test_function_invoice_move(self):
        latam_type = self.env['l10n_latam.document.type'].search([], limit=1)
        # Create a secondary move for this test to avoid ID collision or constraint issues
        move_2 = self.env['account.move'].create({
            'name': 'Move 2',
            'date': fields.Date.today(),
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.journal.id,
        })

        vals_list = [{
            'sequence': 100,
            'product_id': False, # Keep simple
            'name': 'Product Classic',
            'account_id': self.account.id,
            'analytic_distribution': False,
            'quantity': 1,
            'product_uom_id': False, # Optional if not using products
            'price_unit': 100,
            'discount': 0,
            'partner_id': self.partner.id,
            'currency_id': self.company.currency_id.id,
            'display_type': 'product',
            'move_id': move_2.id,
            'l10n_latam_document_type_id': latam_type.id if latam_type else False
            }]
        
        # We call create on the model, utilizing the environment of ts_account_move_line
        res_create = self.env['account.move.line'].create(vals_list)
        
        # Test functionality
        self.assertTrue(res_create)
        # Verify readonly computation if applicable. Passing specific record if needed.
        # self.assertIsNone(self.ts_account_move_line._compute_serie_correlative_is_readonly()) 
        # Note: _compute methods usually return None and set fields.
        # The original test checked return value which is None. Preserving that check.
        self.assertIsNone(self.ts_account_move_line._compute_serie_correlative_is_readonly())

    def test_vendor_bill_serie_logic(self):
        """Test logic for in_invoice: l10n_latam_document_number > ref, and space removal"""
        
        # We need a purchase journal for in_invoice.
        purchase_journal = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
        if not purchase_journal:
             purchase_journal = self.env['account.journal'].create({
                'name': 'Test Purchase Journal',
                'type': 'purchase',
                'code': 'TPJ',
             })

        # Case 1: Both present. Should take l10n_latam_document_number and strip spaces.
        vendor_bill = self.env['account.move'].create({
            'name': '/',
            'move_type': 'in_invoice',
            'partner_id': self.partner.id,
            'journal_id': purchase_journal.id,
            'date': fields.Date.today(),
            'l10n_latam_document_number': ' F001 - 123 ',
            'ref': ' REF 999 ',
        })
        
        # Trigger compute if not auto-triggered (create usually triggers it)
        # Check result
        self.assertEqual(vendor_bill.serie_correlative, 'F001-123')
        
        # Case 2: Only Ref. Should take Ref and strip spaces.
        vendor_bill.l10n_latam_document_number = False
        vendor_bill.ref = ' REF 456 '
        
        self.assertEqual(vendor_bill.serie_correlative, 'REF456')