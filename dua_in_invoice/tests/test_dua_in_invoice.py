from odoo.tests import tagged, Form
from odoo.tests.common import TransactionCase

@tagged('-at_install', 'post_install')
class TestDuaInInvoice(TransactionCase):

    def setUp(self):
        super().setUp()
        self.product = self.env['product.product'].create({'name': 'Producto de Prueba'})

    def test_aduana_fields_activation(self):
        document_type_01 = self.env['l10n_latam.document.type'].search([('code', '=', '01')], limit=1)
        document_type_50 = self.env['l10n_latam.document.type'].search([('code', '=', '50')], limit=1)
        code_aduana = self.env['code.aduana'].search([('code', '=', '19')], limit=1)

        # Factura con tipo de documento diferente de 50
        invoice_01 = self.env['account.move'].create({
            'partner_id': self.env.ref('base.partner_admin').id,
            'move_type': 'in_invoice',
            'invoice_date': '2024-02-01',
            'invoice_line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 1, 'price_unit': 100})],
            'l10n_latam_document_type_id': document_type_01.id
        })
        self.assertFalse(invoice_01.year_aduana, "El campo year_aduana no está activo cuando no debería.")
        self.assertFalse(invoice_01.code_aduana, "El campo code_aduana no está activo cuando no debería.")

        # Factura con tipo de documento igual a 50
        invoice_50 = self.env['account.move'].create({
            'partner_id': self.env.ref('base.partner_admin').id,
            'move_type': 'in_invoice',
            'invoice_date': '2024-02-01',
            'invoice_line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 1, 'price_unit': 100})],
            'l10n_latam_document_type_id': document_type_50.id,
            'year_aduana': '2020',
            'code_aduana': code_aduana.id,
        })
        self.assertTrue(invoice_50.year_aduana, "El campo year_aduana está activo cuando debería.")
        self.assertTrue(invoice_50.code_aduana, "El campo code_aduana está activo cuando debería.")

    def test_onchange_behavior(self):
        """Test that changing document type to non-DUA clears DUA fields."""
        # Find required records
        doc_type_50 = self.env['l10n_latam.document.type'].search([('code', '=', '50')], limit=1)
        doc_type_01 = self.env['l10n_latam.document.type'].search([('code', '=', '01')], limit=1)
        code_aduana_19 = self.env['code.aduana'].search([('code', '=', '19')], limit=1)

        if not doc_type_50 or not doc_type_01:
            self.skipTest("Missing l10n_latam document types 50 or 01, skipping onchange test.")

        # Create a Company in Peru
        company_pe = self.env['res.company'].create({
            'name': 'Test Company PE',
            'country_id': self.env.ref('base.pe').id,
            'currency_id': self.env.ref('base.PEN').id,
        })
        
        # Load PE Chart of Accounts to avoid "Cannot find a chart of accounts" error
        self.env['account.chart.template'].try_loading('pe', company=company_pe, install_demo=False)
        
        # Create a journal that uses documents to ensure l10n_latam_document_type_id is visible
        # Ensure it belongs to the PE company
        journal = self.env['account.journal'].create({
            'name': 'Test Purchase Journal - DUA',
            'type': 'purchase',
            'code': 'TPJ',
            'company_id': company_pe.id,
            'l10n_latam_use_documents': True,
        })

        # Use Form to simulate UI interaction
        # IMPORTANT: Run with the PE company active so view logic (l10n_country_filter) doesn't hide the field
        invoice_form = Form(
            self.env['account.move'].with_company(company_pe).with_context(
                default_move_type='in_invoice', 
                default_journal_id=journal.id
            )
        )
        invoice_form.partner_id = self.env.ref('base.partner_admin')
        
        # Select DUA (50)
        invoice_form.l10n_latam_document_type_id = doc_type_50
        invoice_form.year_aduana = '2024'
        invoice_form.code_aduana = code_aduana_19
        
        # Verify values are set
        self.assertEqual(invoice_form.year_aduana, '2024')
        self.assertEqual(invoice_form.code_aduana, code_aduana_19)

        # Switch to Invoice (01) - Should clear DUA fields
        invoice_form.l10n_latam_document_type_id = doc_type_01
        
        self.assertFalse(invoice_form.year_aduana, "year_aduana should be cleared when switching to non-DUA type")
        self.assertFalse(invoice_form.code_aduana, "code_aduana should be cleared when switching to non-DUA type")

        print('-------------TEST OK-------------')

