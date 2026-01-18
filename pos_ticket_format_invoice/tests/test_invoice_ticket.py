from odoo.tests import common, tagged

@tagged('post_install', '-at_install')
class TestInvoiceTicket(common.TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a journal with point of emission
        cls.journal = cls.env['account.journal'].create({
            'name': 'Ticket Journal',
            'code': 'TKT',
            'type': 'sale',
            'address_point_emission': 'Av. Larco 123, Miraflores',
            # We don't set 'amount_text_format' specifically to 'custom' unless needed, 
            # but usually defaults or mapped to 'es'. 
            # If amount_to_text_invoice is installed, it defaults to 'custom' often or native.
            # Let's trust standard behavior or set it if field exists (checked in dependency).
        })
        
        # Create a product
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'type': 'service',
            'list_price': 100.0,
        })
        
        # Create a partner
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
        })
        
        # Create an invoice
        cls.invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': cls.journal.id,
            'partner_id': cls.partner.id,
            'invoice_date': '2023-01-01',
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': cls.product.id,
                    'quantity': 1,
                    'price_unit': 123.45,
                    'tax_ids': [], # No taxes for simple math
                }),
            ],
        })

    def test_invoice_ticket_logic(self):
        """ Test that the invoice has the correct fields for the ticket report """
        self.invoice.action_post()
        
        # 1. Verify Journal Address (Module specific field)
        self.assertEqual(self.invoice.journal_id.address_point_emission, 'Av. Larco 123, Miraflores')
        
        # 2. Verify Amount to Text Integration (Dependency check)
        # amount_to_text_invoice provides 'amount_total_words'
        self.assertTrue(self.invoice.amount_total_words, "Amount total words should be computed")
        # 123.45 -> ONE HUNDRED TWENTY-THREE... check partially or just type
        self.assertIsInstance(self.invoice.amount_total_words, str)
        print(f"Computed Amount Words: {self.invoice.amount_total_words}")

    def test_report_definition(self):
        """ Verify the report action is correctly defined and linked """
        report = self.env.ref('pos_ticket_format_invoice.account_invoices_tickets')
        self.assertTrue(report)
        self.assertEqual(report.report_name, 'pos_ticket_format_invoice.report_invoice_document_tickets')
        self.assertEqual(report.paperformat_id.name, 'Invoice Ticket')
