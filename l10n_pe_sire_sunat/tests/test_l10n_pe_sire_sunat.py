from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError


@tagged("post_install", "-at_install")
class TestSireSaleWizard(TransactionCase):
    """Tests for the RVIE (Sales) SIRE Wizard — all opportunity codes and edge cases."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.company.write({
            "vat": "20551583041",
            "country_id": cls.env.ref("base.pe").id,
        })
        # Activate PEN if needed (skill: inactive currencies)
        cls.currency_pen = cls.env["res.currency"].with_context(
            active_test=False
        ).search([("name", "=", "PEN")], limit=1)
        if cls.currency_pen and not cls.currency_pen.active:
            cls.currency_pen.active = True

        # Tax group and tax
        cls.tax_group = cls.env["account.tax.group"].create({
            "name": "IGV Test",
            "l10n_pe_edi_code": "IGV",
        })
        cls.tax_18 = cls.env["account.tax"].create({
            "name": "IGV 18% Test",
            "amount_type": "percent",
            "amount": 18,
            "l10n_pe_edi_tax_code": "1000",
            "l10n_pe_edi_unece_category": "S",
            "type_tax_use": "sale",
            "tax_group_id": cls.tax_group.id,
        })

        # Product
        cls.product = cls.env["product.product"].create({
            "name": "SIRE Test Product",
            "lst_price": 1000.0,
        })

        # Partner with Peru identification
        cls.partner = cls.env["res.partner"].create({
            "name": "SIRE Test Partner",
            "vat": "20100047218",
            "l10n_latam_identification_type_id": cls.env.ref("l10n_pe.it_RUC").id,
            "country_id": cls.env.ref("base.pe").id,
        })

        # Create and post a sale invoice for May 2024
        cls.sale_invoice = cls.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": cls.partner.id,
            "invoice_date": "2024-05-15",
            "date": "2024-05-15",
            "currency_id": cls.currency_pen.id,
            "l10n_latam_document_type_id": cls.env.ref("l10n_pe.document_type01").id,
            "invoice_line_ids": [(0, 0, {
                "product_id": cls.product.id,
                "price_unit": 2000.0,
                "quantity": 5,
                "tax_ids": [(6, 0, cls.tax_18.ids)],
            })],
        })
        cls.sale_invoice.action_post()

    def _create_sale_wizard(self, opportunity_code):
        """Helper to create a SIRE Sale Wizard with given opportunity code."""
        return self.env["sire.sale.wizard"].create({
            "company_id": self.company.id,
            "year": "2024",
            "month": "05",
            "state_send": "1",
            "opportunity_code": opportunity_code,
        })

    # --- Test all 4 opportunity codes ---

    def test_sire_sale_accept_proposed(self):
        """RVIE code 01: Accept Proposal generates XLSX and ZIP."""
        wizard = self._create_sale_wizard("01")
        wizard.action_generate_files()
        self.assertTrue(wizard.xlsx_binary, "XLSX should be generated for code 01")
        self.assertTrue(wizard.zip_binary, "ZIP should be generated for code 01")

    def test_sire_sale_replace_proposed(self):
        """RVIE code 02: Replace Proposal generates XLSX and ZIP."""
        wizard = self._create_sale_wizard("02")
        wizard.action_generate_files()
        self.assertTrue(wizard.xlsx_binary, "XLSX should be generated for code 02")
        self.assertTrue(wizard.zip_binary, "ZIP should be generated for code 02")

    def test_sire_sale_subsequent_adjustments(self):
        """RVIE code 03: Subsequent Adjustments generates XLSX and ZIP."""
        wizard = self._create_sale_wizard("03")
        wizard.action_generate_files()
        self.assertTrue(wizard.xlsx_binary, "XLSX should be generated for code 03")
        self.assertTrue(wizard.zip_binary, "ZIP should be generated for code 03")

    def test_sire_sale_general_format(self):
        """RVIE code 04: General Format generates XLSX and ZIP."""
        wizard = self._create_sale_wizard("04")
        wizard.action_generate_files()
        self.assertTrue(wizard.xlsx_binary, "XLSX should be generated for code 04")
        self.assertTrue(wizard.zip_binary, "ZIP should be generated for code 04")

    # --- Edge cases ---

    def test_sire_sale_empty_period(self):
        """Empty period shows error_dialog instead of failing."""
        wizard = self._create_sale_wizard("02")
        # Use a month with no invoices
        wizard.month = "01"
        wizard.action_generate_files()
        self.assertTrue(
            wizard.error_dialog,
            "error_dialog should indicate no data for the period"
        )

    def test_sire_sale_regeneration_clears_previous_files(self):
        """Second generation clears previous binary data before regenerating."""
        wizard = self._create_sale_wizard("02")
        wizard.action_generate_files()
        first_xlsx = wizard.xlsx_binary
        self.assertTrue(first_xlsx)

        # Generate again — the action first clears then regenerates
        wizard.action_generate_files()
        self.assertTrue(wizard.xlsx_binary, "XLSX should exist after regeneration")
        self.assertTrue(wizard.zip_binary, "ZIP should exist after regeneration")


@tagged("post_install", "-at_install")
class TestSirePurchaseNationalWizard(TransactionCase):
    """Tests for the RCE National (Purchase) SIRE Wizard and non-domiciled mutual exclusion."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.company.write({
            "vat": "20551583041",
            "country_id": cls.env.ref("base.pe").id,
        })
        cls.currency_pen = cls.env["res.currency"].with_context(
            active_test=False
        ).search([("name", "=", "PEN")], limit=1)
        if cls.currency_pen and not cls.currency_pen.active:
            cls.currency_pen.active = True

        cls.tax_group = cls.env["account.tax.group"].create({
            "name": "IGV Purchase Test",
            "l10n_pe_edi_code": "IGV",
        })
        cls.tax_18_purchase = cls.env["account.tax"].create({
            "name": "IGV 18% Purchase Test",
            "amount_type": "percent",
            "amount": 18,
            "l10n_pe_edi_tax_code": "1000",
            "l10n_pe_edi_unece_category": "S",
            "type_tax_use": "purchase",
            "tax_group_id": cls.tax_group.id,
        })
        cls.product = cls.env["product.product"].create({
            "name": "SIRE Purchase Test Product",
            "lst_price": 500.0,
        })

        # National partner (not non-domiciled)
        cls.partner_national = cls.env["res.partner"].create({
            "name": "Proveedor Nacional SA",
            "vat": "20100047218",
            "l10n_latam_identification_type_id": cls.env.ref("l10n_pe.it_RUC").id,
            "country_id": cls.env.ref("base.pe").id,
        })

        # Non-domiciled partner
        cls.partner_nodomiciled = cls.env["res.partner"].create({
            "name": "Foreign Supplier LLC",
            "vat": "20998877661",
            "l10n_latam_identification_type_id": cls.env.ref("l10n_pe.it_RUC").id,
            "country_id": cls.env.ref("base.us").id,
        })

        # National purchase invoice — May 2024
        cls.purchase_national = cls.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": cls.partner_national.id,
            "invoice_date": "2024-05-10",
            "date": "2024-05-10",
            "currency_id": cls.currency_pen.id,
            "l10n_latam_document_type_id": cls.env.ref("l10n_pe.document_type01").id,
            "invoice_line_ids": [(0, 0, {
                "product_id": cls.product.id,
                "price_unit": 1000.0,
                "quantity": 3,
                "tax_ids": [(6, 0, cls.tax_18_purchase.ids)],
            })],
        })
        cls.purchase_national.action_post()

        # Non-domiciled purchase invoice — May 2024
        cls.purchase_nodomiciled = cls.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": cls.partner_nodomiciled.id,
            "invoice_date": "2024-05-12",
            "date": "2024-05-12",
            "currency_id": cls.currency_pen.id,
            "l10n_latam_document_type_id": cls.env.ref("l10n_pe.document_type01").id,
            "is_nodomicilied": True,
            "invoice_line_ids": [(0, 0, {
                "product_id": cls.product.id,
                "price_unit": 800.0,
                "quantity": 2,
                "tax_ids": [(6, 0, cls.tax_18_purchase.ids)],
            })],
        })
        cls.purchase_nodomiciled.action_post()

    def test_sire_purchase_national_replace(self):
        """RCE National code 02: Replace Proposal generates files."""
        wizard = self.env["sire.purchase.national.wizard"].create({
            "company_id": self.company.id,
            "year": "2024",
            "month": "05",
            "state_send": "1",
            "opportunity_code": "02",
        })
        wizard.action_generate_files()
        self.assertTrue(wizard.xlsx_binary, "XLSX should be generated for RCE National")
        self.assertTrue(wizard.zip_binary, "ZIP should be generated for RCE National")

    def test_sire_purchase_national_excludes_nodomiciled(self):
        """RCE National must exclude non-domiciled partner invoices from results."""
        wizard = self.env["sire.purchase.national.wizard"].create({
            "company_id": self.company.id,
            "year": "2024",
            "month": "05",
            "state_send": "1",
            "opportunity_code": "02",
        })
        # Execute the query to get raw results
        results = wizard._process_query_results()
        partner_vats = [r.get("partner_vat", "").strip() for r in results]
        self.assertNotIn(
            self.partner_nodomiciled.vat,
            partner_vats,
            "Non-domiciled partner should NOT appear in National purchase report"
        )


@tagged("post_install", "-at_install")
class TestSirePurchaseNotDomiciledWizard(TransactionCase):
    """Tests for the RCE Non-Domiciled (Purchase) SIRE Wizard."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.company.write({
            "vat": "20551583041",
            "country_id": cls.env.ref("base.pe").id,
        })
        cls.currency_pen = cls.env["res.currency"].with_context(
            active_test=False
        ).search([("name", "=", "PEN")], limit=1)
        if cls.currency_pen and not cls.currency_pen.active:
            cls.currency_pen.active = True

        cls.tax_group = cls.env["account.tax.group"].create({
            "name": "IGV NoDom Test",
            "l10n_pe_edi_code": "IGV",
        })
        cls.tax_18_purchase = cls.env["account.tax"].create({
            "name": "IGV 18% NoDom Purchase",
            "amount_type": "percent",
            "amount": 18,
            "l10n_pe_edi_tax_code": "1000",
            "l10n_pe_edi_unece_category": "S",
            "type_tax_use": "purchase",
            "tax_group_id": cls.tax_group.id,
        })
        cls.product = cls.env["product.product"].create({
            "name": "SIRE NoDom Product",
            "lst_price": 500.0,
        })

        # National partner
        cls.partner_national = cls.env["res.partner"].create({
            "name": "Proveedor Nacional Test",
            "vat": "20100047218",
            "l10n_latam_identification_type_id": cls.env.ref("l10n_pe.it_RUC").id,
            "country_id": cls.env.ref("base.pe").id,
        })

        # Non-domiciled partner
        cls.partner_nodomiciled = cls.env["res.partner"].create({
            "name": "Offshore Corp NoDom",
            "vat": "20554433221",
            "l10n_latam_identification_type_id": cls.env.ref("l10n_pe.it_RUC").id,
            "country_id": cls.env.ref("base.us").id,
        })

        # Non-domiciled purchase invoice
        cls.purchase_nodom = cls.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": cls.partner_nodomiciled.id,
            "invoice_date": "2024-05-20",
            "date": "2024-05-20",
            "currency_id": cls.currency_pen.id,
            "l10n_latam_document_type_id": cls.env.ref("l10n_pe.document_type01").id,
            "is_nodomicilied": True,
            "invoice_line_ids": [(0, 0, {
                "product_id": cls.product.id,
                "price_unit": 600.0,
                "quantity": 4,
                "tax_ids": [(6, 0, cls.tax_18_purchase.ids)],
            })],
        })
        cls.purchase_nodom.action_post()

        # National purchase for exclusion test
        cls.purchase_national = cls.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": cls.partner_national.id,
            "invoice_date": "2024-05-22",
            "date": "2024-05-22",
            "currency_id": cls.currency_pen.id,
            "l10n_latam_document_type_id": cls.env.ref("l10n_pe.document_type01").id,
            "invoice_line_ids": [(0, 0, {
                "product_id": cls.product.id,
                "price_unit": 300.0,
                "quantity": 2,
                "tax_ids": [(6, 0, cls.tax_18_purchase.ids)],
            })],
        })
        cls.purchase_national.action_post()

    def test_sire_purchase_nodomiciled_informed(self):
        """RCE Non-domiciled code 00: Informed generates files."""
        wizard = self.env["sire.purchase.not.domiciled.wizard"].create({
            "company_id": self.company.id,
            "year": "2024",
            "month": "05",
            "state_send": "1",
            "opportunity_code": "00",
        })
        wizard.action_generate_files()
        self.assertTrue(wizard.xlsx_binary, "XLSX should be generated for Non-domiciled")
        self.assertTrue(wizard.zip_binary, "ZIP should be generated for Non-domiciled")

    def test_sire_purchase_nodomiciled_excludes_national(self):
        """RCE Non-domiciled must exclude national partner invoices."""
        wizard = self.env["sire.purchase.not.domiciled.wizard"].create({
            "company_id": self.company.id,
            "year": "2024",
            "month": "05",
            "state_send": "1",
            "opportunity_code": "00",
        })
        results = wizard._process_query_results()
        partner_vats = [r.get("partner_vat", "").strip() for r in results]
        self.assertNotIn(
            self.partner_national.vat,
            partner_vats,
            "National partner should NOT appear in Non-domiciled report"
        )


@tagged("post_install", "-at_install")
class TestSirePurchaseComplementsWizard(TransactionCase):
    """Tests for the Purchase Complements Wizard (context-based, from account.move)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.company.write({
            "vat": "20551583041",
            "country_id": cls.env.ref("base.pe").id,
        })
        cls.currency_pen = cls.env["res.currency"].with_context(
            active_test=False
        ).search([("name", "=", "PEN")], limit=1)
        if cls.currency_pen and not cls.currency_pen.active:
            cls.currency_pen.active = True

        cls.tax_group = cls.env["account.tax.group"].create({
            "name": "IGV Complement Test",
            "l10n_pe_edi_code": "IGV",
        })
        cls.tax_18_purchase = cls.env["account.tax"].create({
            "name": "IGV 18% Complement",
            "amount_type": "percent",
            "amount": 18,
            "l10n_pe_edi_tax_code": "1000",
            "l10n_pe_edi_unece_category": "S",
            "type_tax_use": "purchase",
            "tax_group_id": cls.tax_group.id,
        })
        cls.product = cls.env["product.product"].create({
            "name": "SIRE Complement Product",
            "lst_price": 500.0,
        })
        cls.partner = cls.env["res.partner"].create({
            "name": "Complement Vendor",
            "vat": "20100047218",
            "l10n_latam_identification_type_id": cls.env.ref("l10n_pe.it_RUC").id,
            "country_id": cls.env.ref("base.pe").id,
        })

        # Two invoices in the same month (May 2024)
        cls.bill_may_1 = cls.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": cls.partner.id,
            "invoice_date": "2024-05-05",
            "date": "2024-05-05",
            "currency_id": cls.currency_pen.id,
            "l10n_latam_document_type_id": cls.env.ref("l10n_pe.document_type01").id,
            "invoice_line_ids": [(0, 0, {
                "product_id": cls.product.id,
                "price_unit": 400.0,
                "quantity": 2,
                "tax_ids": [(6, 0, cls.tax_18_purchase.ids)],
            })],
        })
        cls.bill_may_1.action_post()

        cls.bill_may_2 = cls.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": cls.partner.id,
            "invoice_date": "2024-05-18",
            "date": "2024-05-18",
            "currency_id": cls.currency_pen.id,
            "l10n_latam_document_type_id": cls.env.ref("l10n_pe.document_type01").id,
            "invoice_line_ids": [(0, 0, {
                "product_id": cls.product.id,
                "price_unit": 600.0,
                "quantity": 1,
                "tax_ids": [(6, 0, cls.tax_18_purchase.ids)],
            })],
        })
        cls.bill_may_2.action_post()

        # One invoice in a different month (June 2024) — for mixed-month test
        cls.bill_june = cls.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": cls.partner.id,
            "invoice_date": "2024-06-10",
            "date": "2024-06-10",
            "currency_id": cls.currency_pen.id,
            "l10n_latam_document_type_id": cls.env.ref("l10n_pe.document_type01").id,
            "invoice_line_ids": [(0, 0, {
                "product_id": cls.product.id,
                "price_unit": 200.0,
                "quantity": 1,
                "tax_ids": [(6, 0, cls.tax_18_purchase.ids)],
            })],
        })
        cls.bill_june.action_post()

    def test_sire_purchase_complements_add(self):
        """Complements wizard with action_taken='add' generates files from selected moves."""
        wizard = self.env["sire.purchase.complements.wizard"].with_context(
            active_model="account.move",
            active_ids=[self.bill_may_1.id, self.bill_may_2.id],
        ).create({
            "company_id": self.company.id,
            "action_taken": "add",
            "correlative": "M1",
        })
        wizard.action_generate_files()
        self.assertTrue(wizard.xlsx_binary, "XLSX should be generated for Complement Add")
        self.assertTrue(wizard.zip_binary, "ZIP should be generated for Complement Add")

    def test_sire_purchase_complements_mixed_month_error(self):
        """Selecting invoices from different months raises UserError."""
        with self.assertRaises(UserError):
            self.env["sire.purchase.complements.wizard"].with_context(
                active_model="account.move",
                active_ids=[self.bill_may_1.id, self.bill_june.id],
            ).create({
                "company_id": self.company.id,
                "action_taken": "add",
                "correlative": "M1",
            })


@tagged("post_install", "-at_install")
class TestSireModelFields(TransactionCase):
    """Tests for custom fields added by the module to account.move and res.company."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.currency_pen = cls.env["res.currency"].with_context(
            active_test=False
        ).search([("name", "=", "PEN")], limit=1)
        if cls.currency_pen and not cls.currency_pen.active:
            cls.currency_pen.active = True

        cls.partner = cls.env["res.partner"].create({
            "name": "Field Test Partner",
            "vat": "20100047218",
            "l10n_latam_identification_type_id": cls.env.ref("l10n_pe.it_RUC").id,
            "country_id": cls.env.ref("base.pe").id,
        })

    def test_account_move_complement_sire_field(self):
        """l10n_pe_is_complement_sire field can be set and read on account.move."""
        move = self.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": self.partner.id,
            "invoice_date": "2024-05-01",
            "date": "2024-05-01",
            "currency_id": self.currency_pen.id,
            "l10n_latam_document_type_id": self.env.ref("l10n_pe.document_type01").id,
        })
        self.assertFalse(
            move.l10n_pe_is_complement_sire,
            "Default value should be False"
        )
        move.l10n_pe_is_complement_sire = True
        self.assertTrue(
            move.l10n_pe_is_complement_sire,
            "Field should be True after setting"
        )

    def test_company_exceeds_1500_uit_field(self):
        """exceeds_1500_uit field can be set and read on res.company."""
        self.assertFalse(
            self.company.exceeds_1500_uit,
            "Default exceeds_1500_uit should be False"
        )
        self.company.exceeds_1500_uit = True
        self.assertTrue(
            self.company.exceeds_1500_uit,
            "exceeds_1500_uit should be True after setting"
        )
