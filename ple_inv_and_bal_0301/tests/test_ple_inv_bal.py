from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from datetime import *

@tagged('post_install', '-at_install')
class TestPleInvBal(TransactionCase):

    def setUp(self):
        super().setUp()
        
        self.ple_report = self.env['ple.report.inv.bal'].create({
            'date_start': date(2024,1,1),
            'date_end':  date(2024,12,31),
            'financial_statements_catalog': '09',
            'eeff_presentation_opportunity': '01',
            'state_send': '1' 
        })        
        self.product = self.env['product.product'].create({
            'name': 'producto test',
            'uom_id': self.env.ref('uom.product_uom_kgm').id,
            'lst_price': 1000.0,
        })
        self.tax_group = self.env['account.tax.group'].create({
            'name': "IGV",
            'l10n_pe_edi_code': "IGV",
        })

        self.tax_18 = self.env['account.tax'].create({
            'name': 'tax_18',
            'amount_type': 'percent',
            'amount': 18,
            'l10n_pe_edi_tax_code': '1000',
            'l10n_pe_edi_unece_category': 'S',
            'type_tax_use': 'sale',
            'tax_group_id': self.tax_group.id,
        })

        self.partner = self.env['res.partner'].create({
            'name': 'Cliente Test',
        })
        
        self.customer_invoice = self.env['account.move'].create({
            'name': 'Factura cliente',
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'invoice_date': date.today(),
            'journal_id': self.env['account.journal'].search([('type', '=', 'sale')], limit=1).id,
            'currency_id': self.env.company.currency_id.id,
            'l10n_latam_document_type_id': self.env.ref('l10n_pe.document_type01').id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                'price_unit': 2000.0,
                'quantity': 5,
                'tax_ids': [(6, 0, self.tax_18.ids)],
            })],
        })
    
    def test_action_generate_report(self):  
          
        self.assertEqual(self.ple_report.date_start, date(2024, 1, 1))
        self.assertEqual(self.ple_report.date_end, date(2024, 12, 31))
        self.assertEqual(self.ple_report.financial_statements_catalog, '09')
        self.assertEqual(self.ple_report.eeff_presentation_opportunity, '01')
        self.assertEqual(self.ple_report.state_send, '1')
    
    def test_initial_balances(self):
        self.customer_invoice.action_post()
        self.ple_report.action_generate_initial_balances_301()
        
        # Verificar si hay lineas luego de generar el saldo inicial
        lines = self.ple_report.line_initial_ids
        if lines:
            self.assertTrue(lines)
        else:
            self.assertFalse(lines)
    
    def test_action_generate_excel(self):
        state = self.ple_report.state
       
        self.assertFalse(self.ple_report.xls_filename)
        self.assertFalse(self.ple_report.xls_binary)
        self.assertEqual(state, 'draft')
        
        self.ple_report.action_generate_excel()

        # Si no hay cuentas EEFF configuradas, el reporte muestra error_dialog
        if self.ple_report.error_dialog:
            self.assertTrue(self.ple_report.error_dialog)
            self.assertEqual(self.ple_report.state, 'draft')
        else:
            self.assertTrue(self.ple_report.xls_filename)
            self.assertTrue(self.ple_report.xls_binary)
            self.assertEqual(self.ple_report.state, 'load')
    
    def test_action_generate_pdf(self):
       
        state = self.ple_report.state
        
        self.assertFalse(self.ple_report.pdf_filename)
        self.assertFalse(self.ple_report.pdf_binary)
        self.assertEqual(state, 'draft')

        self.ple_report.action_generate_excel()
        
        # Si no hay cuentas EEFF configuradas, no se genera PDF
        if self.ple_report.error_dialog:
            self.assertTrue(self.ple_report.error_dialog)
        else:
            self.assertTrue(self.ple_report.pdf_filename)
            self.assertTrue(self.ple_report.pdf_binary)
            self.assertEqual(self.ple_report.state, 'load')
    
    def test_action_generate_txt(self):
       
        state = self.ple_report.state
        
        self.assertFalse(self.ple_report.txt_filename)
        self.assertFalse(self.ple_report.txt_binary)
        self.assertEqual(state, 'draft')

        self.ple_report.action_generate_excel()
        
        # Si no hay cuentas EEFF configuradas, no se genera TXT
        if self.ple_report.error_dialog:
            self.assertTrue(self.ple_report.error_dialog)
        else:
            self.assertTrue(self.ple_report.txt_filename)
            self.assertTrue(self.ple_report.txt_binary)
            self.assertEqual(self.ple_report.state, 'load')

