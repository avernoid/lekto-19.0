from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestPleCashBook(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Company setup — vat and ple_type_contributor are required by SQL queries / filename
        cls.company = cls.env.company
        cls.company.write({
            'country_id': cls.env.ref('base.pe').id,
            'vat': '20551583041',
        })
        # ple_type_contributor is defined in ple_sale_book (base)
        if hasattr(cls.company, 'ple_type_contributor'):
            cls.company.ple_type_contributor = 'CUO'

        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner PLE',
            'email': 'test@example.com',
            'country_id': cls.env.ref('base.pe').id,
        })

        cls.product = cls.env['product.product'].create({
            'name': 'Test Service Product',
            'list_price': 100.0,
            'standard_price': 50.0,
            'type': 'service',
        })

        cls.payment_method = cls.env['payment.methods.codes'].create({
            'code': '003',
            'description': 'Wire Transfer',
        })

        cls.bank_journal = cls.env['account.journal'].search([
            ('type', '=', 'bank'),
            ('company_id', '=', cls.company.id),
        ], limit=1) or cls.env['account.journal'].create({
            'name': 'Test Bank Journal',
            'type': 'bank',
            'code': 'TBK',
            'company_id': cls.company.id,
        })

        cls.cash_journal = cls.env['account.journal'].search([
            ('type', '=', 'cash'),
            ('company_id', '=', cls.company.id),
        ], limit=1) or cls.env['account.journal'].create({
            'name': 'Test Cash Journal',
            'type': 'cash',
            'code': 'TCS',
            'company_id': cls.company.id,
        })

        cls.purchase_journal = cls.env['account.journal'].search([
            ('type', '=', 'purchase'),
            ('company_id', '=', cls.company.id),
        ], limit=1) or cls.env['account.journal'].create({
            'name': 'Test Purchase Journal',
            'type': 'purchase',
            'code': 'TPJ',
            'company_id': cls.company.id,
        })

        cls.document_type = cls.env['l10n_latam.document.type'].search(
            [('country_id.code', '=', 'PE')], limit=1
        )

    # ------------------------------------------------------------------
    # Test 1: Default Payment Method
    # ------------------------------------------------------------------
    def test_payment_means_payment_default(self):
        """Test that means_payment_id defaults to code 003."""
        payment = self.env['account.payment'].create({
            'partner_id': self.partner.id,
            'amount': 100.0,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'journal_id': self.bank_journal.id,
        })
        self.assertTrue(
            payment.means_payment_id,
            "means_payment_id should have a default value"
        )
        self.assertEqual(
            payment.means_payment_id.code,
            '003',
            "Default means_payment_id should be code '003'"
        )

    # ------------------------------------------------------------------
    # Test 2: Report Lifecycle (draft → load → closed → draft)
    # ------------------------------------------------------------------
    def test_ple_report_cash_bank_lifecycle(self):
        """Test the full lifecycle: draft → load → closed → rollback."""
        today = fields.Date.today()
        report = self.env['ple.report.cash.bank'].create({
            'company_id': self.company.id,
            'date_start': today.replace(day=1),
            'date_end': today,
            'state_send': '1',
        })

        # Initial state
        self.assertEqual(report.state, 'draft')

        # Generate report
        report.action_generate_excel()
        self.assertEqual(report.state, 'load', "State should be 'load' after generation")

        # Verify binary files are generated (even if empty content, they should exist)
        self.assertTrue(report.txt_binary_cash, "Cash TXT should be generated")
        self.assertTrue(report.txt_binary_bank, "Bank TXT should be generated")
        self.assertTrue(report.xls_binary_cash, "Cash Excel should be generated")
        self.assertTrue(report.xls_binary_bank, "Bank Excel should be generated")

        # Verify TXT filenames follow PLE naming convention: LE{RUC}...
        self.assertTrue(
            report.txt_filename_cash and report.txt_filename_cash.startswith('LE'),
            "Cash TXT filename should start with 'LE'"
        )
        self.assertTrue(
            report.txt_filename_bank and report.txt_filename_bank.startswith('LE'),
            "Bank TXT filename should start with 'LE'"
        )
        # Verify VAT is embedded in filename
        self.assertIn(
            self.company.vat,
            report.txt_filename_cash,
            "Cash TXT filename should contain company VAT"
        )

        # Close (declare to SUNAT)
        report.action_close()
        self.assertEqual(report.state, 'closed', "State should be 'closed' after declaration")

        # Rollback
        report.action_rollback()
        self.assertEqual(report.state, 'draft', "State should be 'draft' after rollback")
        self.assertFalse(report.txt_binary_cash, "Cash TXT should be cleared after rollback")
        self.assertFalse(report.txt_binary_bank, "Bank TXT should be cleared after rollback")
        self.assertFalse(report.xls_binary_cash, "Cash Excel should be cleared after rollback")
        self.assertFalse(report.xls_binary_bank, "Bank Excel should be cleared after rollback")

    # ------------------------------------------------------------------
    # Test 3: inv computed field — Bank journal (True) vs Cash journal (False)
    # ------------------------------------------------------------------
    def test_payment_register_inv_compute_bank(self):
        """Test that inv=True for bank journals (shows payment method)."""
        invoice = self._create_and_post_vendor_bill()

        register = self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=invoice.ids,
        ).create({
            'journal_id': self.bank_journal.id,
        })
        self.assertTrue(
            register.inv,
            "inv should be True for bank journals (shows means_payment_id)"
        )

    def test_payment_register_inv_compute_cash(self):
        """Test that inv=False for cash journals (hides payment method)."""
        invoice = self._create_and_post_vendor_bill()

        register = self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=invoice.ids,
        ).create({
            'journal_id': self.cash_journal.id,
        })
        self.assertFalse(
            register.inv,
            "inv should be False for cash journals (hides means_payment_id)"
        )

    # ------------------------------------------------------------------
    # Test 4: Bank ID on account.account
    # ------------------------------------------------------------------
    def test_account_bank_id_assignment(self):
        """Test that bank_id can be assigned to a cash-type account."""
        bank = self.env['res.partner.bank'].search([], limit=1)
        if not bank:
            bank = self.env['res.partner.bank'].create({
                'acc_number': '123456789',
                'partner_id': self.company.partner_id.id,
            })

        account = self.env['account.account'].create({
            'name': 'Test Cash Account PLE',
            'code': '101099',
            'account_type': 'asset_cash',
            'company_ids': [(4, self.company.id)],
        })
        account.bank_id = bank
        self.assertEqual(
            account.bank_id.id, bank.id,
            "bank_id should be assignable to cash-type accounts"
        )

    # ------------------------------------------------------------------
    # Test 5: ple_selection extension
    # ------------------------------------------------------------------
    def test_ple_selection_values(self):
        """Test that ple_selection includes cash and bank options."""
        field = self.env['account.account']._fields['ple_selection']
        selection_keys = [key for key, _ in field.selection]
        self.assertIn('cash', selection_keys, "ple_selection should include 'cash'")
        self.assertIn('bank', selection_keys, "ple_selection should include 'bank'")

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------
    def _create_and_post_vendor_bill(self):
        """Create and post a minimal vendor bill for payment register tests."""
        invoice = self.env['account.move'].create({
            'partner_id': self.partner.id,
            'move_type': 'in_invoice',
            'invoice_date': fields.Date.today(),
            'journal_id': self.purchase_journal.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 100.0,
            })],
        })
        # Set document type only if the field exists and a type is available
        if self.document_type and hasattr(invoice, 'l10n_latam_document_type_id'):
            invoice.l10n_latam_document_type_id = self.document_type.id
            invoice.l10n_latam_document_number = 'F001-000001'
        invoice.action_post()
        return invoice
