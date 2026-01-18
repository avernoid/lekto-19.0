from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestInvoiceExtras(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})
        cls.invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner.id,
            'invoice_date': '2026-01-01',
        })

    def test_fields_existence_and_persistence(self):
        """
        Test that the new fields exist and can store values.
        """
        # 1. Test Carrier Reference Number (on Invoice)
        carrier_ref = "GR-001-123456"
        self.invoice.carrier_ref_number = carrier_ref
        self.assertEqual(self.invoice.carrier_ref_number, carrier_ref, 
                         "Carrier Reference Number was not stored correctly.")

        # 2. Test Additional Document Reference (on Invoice)
        doc_ref = "OC-999"
        self.invoice.aditional_document_reference = doc_ref
        self.assertEqual(self.invoice.aditional_document_reference, doc_ref, 
                         "Additional Document Reference was not stored correctly.")

        # 3. Test Additional Information (on Company)
        # This is an HTML field.
        extra_info = "<p>Thank you for your business.</p>"
        self.company.additional_information = extra_info
        self.assertEqual(self.company.additional_information, extra_info, 
                         "Company Additional Information was not stored correctly.")

    def test_fields_on_invoice_report_context(self):
        """
        Verify that the fields are accessible in the object context used by reports.
        """
        # Ensure the values are set
        self.company.additional_information = "<div>Report Info</div>"
        
        # In a real report rendering, 'o' is the account.move record.
        # We simulate checking if 'o.company_id.additional_information' is accessible.
        invoice_company_info = self.invoice.company_id.additional_information
        self.assertEqual(invoice_company_info, "<div>Report Info</div>",
                         "Invoice should be able to access company additional info.")
