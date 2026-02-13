from pytz import timezone
from datetime import datetime,date

from odoo.tests.common import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import common


@tagged('post_install', '-at_install')
class TestPleLedgerBook(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.frozen_today = datetime(year=2024, month=5, day=31, hour=0, minute=0, second=0, tzinfo=timezone('utc'))

        cls.company_data = cls.env['res.company'].create({
            'name':'Company Peruvian',
            'vat': "20557912879",
            'country_id': cls.env.ref('base.pe').id,
        })
        
        cls.tax_group = cls.env['account.tax.group'].create({
            'name': "IGV",
            'l10n_pe_edi_code': "IGV",
        })

        cls.tax_18 = cls.env['account.tax'].create({
            'name': 'tax_18',
            'amount_type': 'percent',
            'amount': 18,
            'l10n_pe_edi_tax_code': '1000',
            'l10n_pe_edi_unece_category': 'S',
            'type_tax_use': 'sale',
            'tax_group_id': cls.tax_group.id,
        })

        cls.product = cls.env['product.product'].create({
            'name': 'product_ple',
            'uom_id': cls.env.ref('uom.product_uom_kgm').id,
            'lst_price': 1000.0,
        })
        
        cls.partner_a = cls.env['res.partner'].create({
            'name':'Comperuvian',
            'vat': '20462509236',
            'l10n_latam_identification_type_id': cls.env.ref('l10n_pe.it_RUC').id,
            'country_id': cls.env.ref('base.pe').id,
        })        
        
        cls.time_name = datetime.now().strftime('%H%M%S')
        
        cls.currency_data = cls.env.ref('base.PEN')
        cls.currency_data.active = True
        
        
    def setUp(self):
        super(TestPleLedgerBook, self).setUp()
    
        self.move_purchase = self.env['account.move'].create({
            'name': 'F FFI-%s1' % self.time_name,
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': date.today(),
            'date': date.today(),
            'journal_id':self.env['account.journal'].search([('type','=','purchase')],limit=1).id,
            'currency_id': self.currency_data.id,
            'invoice_currency_rate': 1.000000,
            'origin_l10n_latam_document_type_id': self.env.ref('l10n_pe.document_type01').id,
            'l10n_latam_document_type_id': self.env.ref('l10n_pe.document_type01').id,
            'invoice_line_ids': [(0, 0, {
                'name':'product purchase',
                'product_id': self.product.id,
                'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                'price_unit': 2000.0,
                'quantity': 5,
                'tax_ids': [(6, 0, self.tax_18.ids)],
            })],
        })
        
        self.move_sale = self.env['account.move'].create({
            'name': 'F FFI-%s2' % self.time_name,
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': date.today(),
            'date': date.today(),
            'journal_id':self.env['account.journal'].search([('type','=','sale')],limit=1).id,
            'currency_id': self.currency_data.id,
            'invoice_currency_rate': 1.000000,
            'origin_l10n_latam_document_type_id': self.env.ref('l10n_pe.document_type01').id,
            'l10n_latam_document_type_id': self.env.ref('l10n_pe.document_type01').id,
            'invoice_line_ids': [(0, 0, {
                'name':'product sale',
                'product_id': self.product.id,
                'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                'price_unit': 1000.0,
                'quantity': 15,
                'tax_ids': [(6, 0, self.tax_18.ids)],
            })],
        })

    def test_ple_ledger_book_purchase(self):
    
        self.move_purchase.company_id.vat = '20557912879'
        self.move_purchase.action_post()
        self.move_purchase.action_register_payment()
        ple_ledger_book = self.env['ple.report.ledger'].create({
            'date_start': date.today(),
            'date_end': date.today(),
            'company_id': self.company_data.id,
            'state_send': '1',
        })
        ple_ledger_book.action_generate_excel()        
        self.assertTrue(ple_ledger_book.xls_binary_ledger)
        self.assertTrue(ple_ledger_book.txt_binary_ledger)
    
    def test_ple_ledger_book_sale(self):
    
        self.move_sale.company_id.vat = '20557912879'
        self.move_sale.action_post()
        self.move_sale.action_register_payment()
        ple_ledger_book = self.env['ple.report.ledger'].create({
            'date_start': date.today(),
            'date_end': date.today(),
            'company_id': self.company_data.id,
            'state_send': '1',
        })
        ple_ledger_book.action_generate_excel()        
        self.assertTrue(ple_ledger_book.xls_binary_ledger)
        self.assertTrue(ple_ledger_book.txt_binary_ledger)
        
    def test_action_rollback(self):
        
        self.move_purchase.action_post()
        ple_ledger_book = self.env['ple.report.ledger'].create({
            'date_start': date.today(),
            'date_end': date.today(),
            'company_id': self.company_data.id,
            'state_send': '1',
        })
        
        ple_ledger_book.action_generate_excel()
        ple_ledger_book.action_rollback()
                
        self.assertFalse(ple_ledger_book.xls_binary_ledger)
        self.assertFalse(ple_ledger_book.txt_binary_ledger)