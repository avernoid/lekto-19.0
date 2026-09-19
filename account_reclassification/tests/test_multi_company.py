from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestReclassificationMultiCompany(AccountTestInvoicingCommon):
    """The reclassification setup of a shared account belongs to each company.

    ``account.account`` is shared between companies through ``company_ids``, so a
    single global value cannot serve two of them: the second company would book
    its reclassification against the journal and the accounts of the first. These
    tests pin the two halves of the fix — the setup being company dependent, and
    the company consistency being *validated* instead of blowing up at posting
    time, where the savepoint swallowed it and the bill posted without its entry.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.company_data["company"]
        cls.company_data_2 = cls.setup_other_company()
        cls.company_b = cls.company_data_2["company"]

        # --- One single account, shared by both companies -------------------
        # A shared account needs its code declared for every company it belongs
        # to, hence `code_mapping_ids` instead of a plain `code`.
        cls.shared_source = cls.env["account.account"].create({
            "name": "Shared reclass source",
            "account_type": "expense",
            "code_mapping_ids": [
                Command.create({"company_id": cls.company_a.id, "code": "RECLSRCA"}),
                Command.create({"company_id": cls.company_b.id, "code": "RECLSRCB"}),
            ],
            "company_ids": [Command.set((cls.company_a + cls.company_b).ids)],
        })

        # --- Each company brings its own journals and its own 60/61 ---------
        cls.mirror_journal_a = cls.env["account.journal"].create({
            "name": "Reclassification A",
            "code": "RCLA",
            "type": "general",
            "company_id": cls.company_a.id,
        })
        cls.mirror_journal_b = cls.env["account.journal"].create({
            "name": "Reclassification B",
            "code": "RCLB",
            "type": "general",
            "company_id": cls.company_b.id,
        })
        cls.target_a = cls.copy_account(
            cls.company_data["default_account_expense"], {"name": "60 Purchases A"})
        cls.counterpart_a = cls.copy_account(
            cls.company_data["default_account_expense"], {"name": "61 Stock Variation A"})
        cls.target_b = cls.copy_account(
            cls.company_data_2["default_account_expense"], {"name": "60 Purchases B"})
        cls.counterpart_b = cls.copy_account(
            cls.company_data_2["default_account_expense"], {"name": "61 Stock Variation B"})

        cls.purchase_journal_a = cls.company_data["default_journal_purchase"]
        cls.purchase_journal_b = cls.company_data_2["default_journal_purchase"]

        # --- The same shared account, configured once per company -----------
        cls.shared_source.with_company(cls.company_a).write({
            "reclass_mirror_mode": "always",
            "reclass_target_account_id": cls.target_a.id,
            "reclass_counterpart_account_id": cls.counterpart_a.id,
            "reclass_mirror_journal_id": cls.mirror_journal_a.id,
        })
        cls.shared_source.with_company(cls.company_b).write({
            "reclass_mirror_mode": "always",
            "reclass_target_account_id": cls.target_b.id,
            "reclass_counterpart_account_id": cls.counterpart_b.id,
            "reclass_mirror_journal_id": cls.mirror_journal_b.id,
        })

        cls.product_shared = cls.env["product.product"].create({
            "name": "Shared reclass product",
            "supplier_taxes_id": [Command.clear()],
        })

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _create_bill(self, company, journal):
        return self.env["account.move"].with_company(company).create({
            "move_type": "in_invoice",
            "partner_id": self.partner_a.id,
            "journal_id": journal.id,
            "invoice_date": "2026-03-15",
            "date": "2026-03-15",
            "invoice_line_ids": [Command.create({
                "product_id": self.product_shared.id,
                "name": "Shared reclass line",
                "account_id": self.shared_source.id,
                "quantity": 1.0,
                "price_unit": 100.0,
                "tax_ids": [Command.clear()],
            })],
        })

    # -------------------------------------------------------------------------
    # TESTS
    # -------------------------------------------------------------------------

    def test_01_setup_is_stored_per_company(self):
        """One shared account holds one setup per company, not a single global one."""
        in_a = self.shared_source.with_company(self.company_a)
        in_b = self.shared_source.with_company(self.company_b)

        self.assertEqual(in_a.reclass_target_account_id, self.target_a)
        self.assertEqual(in_a.reclass_counterpart_account_id, self.counterpart_a)
        self.assertEqual(in_a.reclass_mirror_journal_id, self.mirror_journal_a)

        self.assertEqual(in_b.reclass_target_account_id, self.target_b)
        self.assertEqual(in_b.reclass_counterpart_account_id, self.counterpart_b)
        self.assertEqual(in_b.reclass_mirror_journal_id, self.mirror_journal_b)

        self.assertNotEqual(
            in_a.reclass_target_account_id, in_b.reclass_target_account_id,
            "Configuring the second company must not overwrite the first one")

    def test_02_mode_is_per_company_too(self):
        """A company may switch the reclassification off without touching the other."""
        self.shared_source.with_company(self.company_b).reclass_mirror_mode = "none"

        self.assertEqual(
            self.shared_source.with_company(self.company_a).reclass_mirror_mode, "always",
            "Switching company B off must leave company A untouched")
        self.assertEqual(
            self.shared_source.with_company(self.company_b).reclass_mirror_mode, "none")

    def test_03_each_company_books_against_its_own_accounts(self):
        """The bill of each company produces its own entry, in its own journal."""
        bill_a = self._create_bill(self.company_a, self.purchase_journal_a)
        bill_a.action_post()
        mirror_a = bill_a.reclass_mirror_move_id
        self.assertTrue(mirror_a, "Company A must get its reclassification entry")
        self.assertEqual(mirror_a.company_id, self.company_a)
        self.assertEqual(mirror_a.journal_id, self.mirror_journal_a)
        self.assertEqual(
            mirror_a.line_ids.account_id, self.target_a | self.counterpart_a)

        bill_b = self._create_bill(self.company_b, self.purchase_journal_b)
        bill_b.action_post()
        mirror_b = bill_b.reclass_mirror_move_id
        self.assertTrue(
            mirror_b,
            "Company B must get its own entry; with a single global setup the "
            "entry failed to be created and the failure was swallowed")
        self.assertEqual(mirror_b.company_id, self.company_b)
        self.assertEqual(mirror_b.journal_id, self.mirror_journal_b)
        self.assertEqual(
            mirror_b.line_ids.account_id, self.target_b | self.counterpart_b,
            "Company B must not book against the accounts of company A")

    def test_04_journal_of_another_company_is_rejected(self):
        """Pointing the setup at another company's journal fails at configuration."""
        with self.assertRaises(UserError):
            self.shared_source.with_company(self.company_a).write({
                "reclass_mirror_journal_id": self.mirror_journal_b.id,
            })

    def test_05_account_of_another_company_is_rejected(self):
        """Same guard on the target account, which is what the engine books to."""
        with self.assertRaises(UserError):
            self.shared_source.with_company(self.company_a).write({
                "reclass_target_account_id": self.target_b.id,
            })
