from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestReclassificationMirror(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]

        # --- Journals -------------------------------------------------------
        cls.mirror_journal = cls.env["account.journal"].create({
            "name": "Accounting Reclassification",
            "code": "RECL",
            "type": "general",
            "company_id": cls.company.id,
        })
        cls.purchase_journal = cls.company_data["default_journal_purchase"]
        cls.purchase_journal.write({
            "generate_reclass_mirror": True,
            "reclass_mirror_journal_id": cls.mirror_journal.id,
        })
        # Second purchase journal deliberately left without the checkbox.
        cls.purchase_journal_off = cls.env["account.journal"].create({
            "name": "Purchases without Reclass flag",
            "code": "BILL2",
            "type": "purchase",
            "company_id": cls.company.id,
            "generate_reclass_mirror": False,
            "reclass_mirror_journal_id": cls.mirror_journal.id,
        })

        # --- Accounts -------------------------------------------------------
        expense = cls.company_data["default_account_expense"]
        cls.account_60 = cls.copy_account(expense, {"name": "Reclass 60 Purchases"})
        cls.account_61 = cls.copy_account(expense, {"name": "Reclass 61 Stock Variation"})
        cls.account_60_categ = cls.copy_account(expense, {"name": "Reclass 60211 by category"})
        # Destination account of the bill line, Reclass enabled.
        cls.account_dest = cls.copy_account(expense, {"name": "Reclass destination"})
        cls.account_dest.write({
            "reclass_mirror_mode": "journal",
            "reclass_target_account_id": cls.account_60.id,
            "reclass_counterpart_account_id": cls.account_61.id,
        })
        # Destination account without any reclassification setup.
        cls.account_plain = cls.copy_account(expense, {"name": "Plain destination"})

        # --- Product categories ---------------------------------------------
        cls.categ_parent = cls.env["product.category"].create({"name": "Reclass Parent"})
        cls.categ_child = cls.env["product.category"].create({
            "name": "Reclass Child",
            "parent_id": cls.categ_parent.id,
        })
        cls.categ_grand_child = cls.env["product.category"].create({
            "name": "Reclass Grand Child",
            "parent_id": cls.categ_child.id,
        })

        cls.product_reclass = cls.env["product.product"].create({
            "name": "Reclass Product",
            "categ_id": cls.categ_grand_child.id,
            "supplier_taxes_id": [Command.clear()],
        })

        cls.bill_date = fields.Date.from_string("2026-03-15")

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _create_bill(self, account=None, journal=None, date=None, move_type="in_invoice",
                     price_unit=1000.0, quantity=2.0, currency=None, analytic=None):
        line_vals = {
            "product_id": self.product_reclass.id,
            "name": "Reclass line",
            "account_id": (account or self.account_dest).id,
            "quantity": quantity,
            "price_unit": price_unit,
            "tax_ids": [Command.clear()],
        }
        if analytic is not None:
            line_vals["analytic_distribution"] = analytic
        vals = {
            "move_type": move_type,
            "partner_id": self.partner_a.id,
            "invoice_date": date or self.bill_date,
            "date": date or self.bill_date,
            "journal_id": (journal or self.purchase_journal).id,
            "invoice_line_ids": [Command.create(line_vals)],
        }
        if currency:
            vals["currency_id"] = currency.id
        return self.env["account.move"].create(vals)

    def _mirrors_of(self, bill):
        return self.env["account.move"].search([("reclass_source_move_id", "=", bill.id)])

    # -------------------------------------------------------------------------
    # 1. CATEGORY FALLBACK
    # -------------------------------------------------------------------------

    def test_01_category_production_account_fallback(self):
        """The account is inherited recursively from the closest ancestor."""
        # Nothing configured anywhere -> empty recordset, no exception.
        self.assertFalse(self.categ_grand_child._reclass_get_production_account())
        self.assertFalse(self.categ_grand_child.reclass_effective_production_account_id)

        # Configured two levels up -> inherited by the whole branch.
        self.categ_parent.reclass_production_account_id = self.account_60_categ
        self.assertEqual(
            self.categ_grand_child._reclass_get_production_account(), self.account_60_categ)
        self.assertEqual(
            self.categ_child._reclass_get_production_account(), self.account_60_categ)
        self.categ_grand_child.invalidate_recordset(["reclass_effective_production_account_id"])
        self.assertEqual(
            self.categ_grand_child.reclass_effective_production_account_id, self.account_60_categ)

        # The closest ancestor wins over the farthest one.
        self.categ_child.reclass_production_account_id = self.account_60
        self.assertEqual(
            self.categ_grand_child._reclass_get_production_account(), self.account_60)

        # Its own value wins over any ancestor.
        self.categ_grand_child.reclass_production_account_id = self.account_61
        self.assertEqual(
            self.categ_grand_child._reclass_get_production_account(), self.account_61)

    # -------------------------------------------------------------------------
    # 2. HAPPY PATH
    # -------------------------------------------------------------------------

    def test_02_mirror_generated_on_post(self):
        """Posting a configured bill creates a balanced 60/61 mirror entry."""
        bill = self._create_bill()
        bill.action_post()

        mirror = bill.reclass_mirror_move_id
        self.assertTrue(mirror, "The mirror entry should have been generated")
        self.assertEqual(mirror.state, "posted")
        self.assertEqual(mirror.move_type, "entry")
        self.assertEqual(mirror.journal_id, self.mirror_journal)
        self.assertEqual(mirror.date, bill.date)
        self.assertEqual(mirror.reclass_source_move_id, bill)
        self.assertEqual(mirror.company_id, bill.company_id)

        self.assertRecordValues(
            mirror.line_ids.sorted(lambda l: l.debit, reverse=True),
            [
                {
                    "account_id": self.account_60.id,
                    "debit": 2000.0,
                    "credit": 0.0,
                    "product_id": self.product_reclass.id,
                    "quantity": 2.0,
                },
                {
                    "account_id": self.account_61.id,
                    "debit": 0.0,
                    "credit": 2000.0,
                    "product_id": self.product_reclass.id,
                    "quantity": 2.0,
                },
            ],
        )
        self.assertEqual(sum(mirror.line_ids.mapped("balance")), 0.0)
        # The native bill is untouched: only its own lines, no extra account.
        self.assertNotIn(
            self.account_60, bill.line_ids.mapped("account_id"),
            "The mirror must never write into the bill itself")

    def test_03_category_production_account_does_not_touch_the_mirror(self):
        """The category production account belongs to the stock flow, not here."""
        self.categ_parent.reclass_production_account_id = self.account_60_categ
        bill = self._create_bill()
        bill.action_post()

        debit_line = bill.reclass_mirror_move_id.line_ids.filtered(lambda l: l.debit)
        self.assertEqual(debit_line.account_id, self.account_60)
        credit_line = bill.reclass_mirror_move_id.line_ids.filtered(lambda l: l.credit)
        self.assertEqual(credit_line.account_id, self.account_61)
        self.assertNotIn(
            self.account_60_categ,
            bill.reclass_mirror_move_id.line_ids.mapped("account_id"))

    # -------------------------------------------------------------------------
    # 3. HARMLESS FALLBACK
    # -------------------------------------------------------------------------

    def test_04_no_configuration_posts_natively(self):
        """A bill without category accounts posts natively, with no mirror and no error."""
        bill = self._create_bill(account=self.account_plain)
        bill.action_post()

        self.assertEqual(bill.state, "posted")
        self.assertFalse(bill.reclass_mirror_move_id)
        self.assertFalse(self._mirrors_of(bill))
        self.assertFalse(bill.reclass_mirror_applicable)

    def test_05_journal_check_required_and_missing(self):
        """Mode 'journal' + journal flag off -> nothing is generated."""
        bill = self._create_bill(journal=self.purchase_journal_off)
        self.assertEqual(self.account_dest.reclass_mirror_mode, "journal")
        bill.action_post()

        self.assertEqual(bill.state, "posted")
        self.assertFalse(bill.reclass_mirror_move_id)
        # The manual button explains why instead of failing silently.
        with self.assertRaisesRegex(UserError, "reclassification setup"):
            bill.action_reclass_generate_mirror()

    # -------------------------------------------------------------------------
    # 4. UNCONDITIONAL BY ACCOUNT
    # -------------------------------------------------------------------------

    def test_06_account_unconditional_ignores_journal_flag(self):
        """Mode 'always' -> the mirror is generated whatever the journal."""
        self.account_dest.reclass_mirror_mode = "always"
        bill = self._create_bill(journal=self.purchase_journal_off)
        self.assertFalse(self.purchase_journal_off.generate_reclass_mirror)

        bill.action_post()

        mirror = bill.reclass_mirror_move_id
        self.assertTrue(mirror, "The account setup alone must trigger the mirror entry")
        self.assertEqual(mirror.state, "posted")
        self.assertEqual(mirror.journal_id, self.mirror_journal)
        self.assertEqual(
            mirror.line_ids.filtered(lambda l: l.debit).account_id, self.account_60)

    # -------------------------------------------------------------------------
    # 5. IDEMPOTENCE
    # -------------------------------------------------------------------------

    def test_07_regeneration_is_idempotent(self):
        """Regenerating many times always leaves exactly one active mirror entry."""
        bill = self._create_bill()
        bill.action_post()
        first_mirror = bill.reclass_mirror_move_id
        self.assertTrue(first_mirror)

        for _index in range(3):
            bill.action_reclass_generate_mirror()

        active = self._mirrors_of(bill).filtered(lambda m: m.state != "cancel")
        self.assertEqual(len(active), 1, "Only one active mirror entry may remain")
        self.assertEqual(bill.reclass_mirror_move_id, active)
        self.assertEqual(active.state, "posted")
        self.assertEqual(first_mirror.state, "cancel",
                         "The superseded mirror entry must be cancelled, not duplicated")
        self.assertEqual(
            sum(self._mirrors_of(bill).filtered(lambda m: m.state == "posted").mapped(
                lambda m: sum(m.line_ids.mapped("debit")))),
            2000.0,
            "The accounting impact must not be multiplied by the regenerations")

    def test_08_regeneration_after_late_configuration(self):
        """A bill posted before the setup can be mirrored on demand afterwards."""
        bill = self._create_bill(account=self.account_plain)
        bill.action_post()
        self.assertFalse(bill.reclass_mirror_move_id)

        self.account_plain.write({
            "reclass_mirror_mode": "journal",
            "reclass_target_account_id": self.account_60.id,
            "reclass_counterpart_account_id": self.account_61.id,
        })
        bill.action_reclass_generate_mirror()

        self.assertTrue(bill.reclass_mirror_move_id)
        self.assertEqual(bill.reclass_mirror_move_id.state, "posted")

    # -------------------------------------------------------------------------
    # 6. RESET TO DRAFT / CANCEL / DELETE
    # -------------------------------------------------------------------------

    def test_09_reset_to_draft_cancels_mirror(self):
        """Resetting the bill to draft cancels and unlinks its mirror entry."""
        bill = self._create_bill()
        bill.action_post()
        mirror = bill.reclass_mirror_move_id
        self.assertEqual(mirror.state, "posted")

        bill.button_draft()

        self.assertEqual(bill.state, "draft")
        self.assertEqual(mirror.state, "cancel")
        self.assertFalse(bill.reclass_mirror_move_id)
        self.assertFalse(self._mirrors_of(bill).filtered(lambda m: m.state != "cancel"))

        # Re-posting rebuilds a single active mirror entry.
        bill.action_post()
        self.assertTrue(bill.reclass_mirror_move_id)
        self.assertEqual(
            len(self._mirrors_of(bill).filtered(lambda m: m.state != "cancel")), 1)

    def test_10_cancel_bill_cancels_mirror(self):
        """Cancelling the bill cancels its mirror entry as well."""
        bill = self._create_bill()
        bill.action_post()
        mirror = bill.reclass_mirror_move_id

        bill.button_cancel()

        self.assertEqual(bill.state, "cancel")
        self.assertEqual(mirror.state, "cancel")
        self.assertFalse(bill.reclass_mirror_move_id)

    def test_11_unlink_bill_cleans_mirror(self):
        """Deleting the bill leaves no active mirror entry behind."""
        bill = self._create_bill()
        bill.action_post()
        bill.button_draft()
        mirror = self._mirrors_of(bill)
        self.assertEqual(mirror.state, "cancel")

        bill.unlink()

        self.assertTrue(mirror.exists())
        self.assertFalse(mirror.reclass_source_move_id)
        self.assertEqual(mirror.state, "cancel")

    # -------------------------------------------------------------------------
    # 7. LOCKED PERIOD
    # -------------------------------------------------------------------------

    def test_12_locked_period_blocks_regeneration(self):
        """Regenerating over a locked period raises a UserError."""
        bill = self._create_bill()
        bill.action_post()
        mirror = bill.reclass_mirror_move_id
        self.assertEqual(mirror.state, "posted")

        self.company.sudo().write({
            "fiscalyear_lock_date": fields.Date.from_string("2026-03-31"),
        })

        with self.assertRaisesRegex(UserError, "cannot add/modify entries prior to"):
            bill.action_reclass_generate_mirror()

        # Nothing was touched by the aborted regeneration.
        self.assertEqual(mirror.state, "posted")
        self.assertEqual(bill.reclass_mirror_move_id, mirror)

    def test_13_locked_period_blocks_first_generation(self):
        """A bill posted before the lock cannot get a new mirror once locked."""
        bill = self._create_bill(account=self.account_plain)
        bill.action_post()

        self.account_plain.write({
            "reclass_mirror_mode": "journal",
            "reclass_target_account_id": self.account_60.id,
            "reclass_counterpart_account_id": self.account_61.id,
        })
        self.company.sudo().write({
            "fiscalyear_lock_date": fields.Date.from_string("2026-03-31"),
        })

        with self.assertRaisesRegex(UserError, "cannot add/modify entries prior to"):
            bill.action_reclass_generate_mirror()
        self.assertFalse(bill.reclass_mirror_move_id)

    # -------------------------------------------------------------------------
    # EXTRA COVERAGE: refunds, currency, analytics
    # -------------------------------------------------------------------------

    def test_14_refund_reverses_the_mirror(self):
        """The target follows the side of the mirrored line; the counterpart inverts."""
        refund = self._create_bill(move_type="in_refund")
        refund.action_post()

        # On a credit note the mirrored line sits on the credit side...
        source_line = refund.invoice_line_ids
        self.assertLess(source_line.balance, 0.0)
        mirror = refund.reclass_mirror_move_id
        self.assertTrue(mirror)
        self.assertRecordValues(
            mirror.line_ids.sorted(lambda l: l.debit, reverse=True),
            [
                # ... so the counterpart takes the debit ...
                {"account_id": self.account_61.id, "debit": 2000.0, "credit": 0.0},
                # ... and the target stays on the credit, like its source line.
                {"account_id": self.account_60.id, "debit": 0.0, "credit": 2000.0},
            ],
        )

    def test_15_foreign_currency_converted_to_company_currency(self):
        """Amounts are mirrored in the company currency."""
        foreign = self.setup_other_currency("EUR")
        bill = self._create_bill(currency=foreign)
        bill.action_post()

        self.assertEqual(bill.currency_id, foreign)
        mirror = bill.reclass_mirror_move_id
        self.assertTrue(mirror)
        source_line = bill.invoice_line_ids
        # Rate 2.0: 2 x 1000 EUR on the bill -> 1000 in company currency.
        self.assertEqual(source_line.amount_currency, 2000.0)
        self.assertEqual(source_line.balance, 1000.0)
        self.assertEqual(mirror.line_ids.filtered(lambda l: l.debit).debit, 1000.0)
        self.assertEqual(
            mirror.line_ids.filtered(lambda l: l.debit).debit, source_line.balance)
        self.assertEqual(
            mirror.line_ids.mapped("currency_id"),
            self.company.currency_id,
            "The mirror entry must be booked in the company currency")
        self.assertEqual(sum(mirror.line_ids.mapped("balance")), 0.0)

    def test_17_journal_fallback_chain(self):
        """Account journal -> journal of the bill -> company default -> nothing."""
        account_journal = self.env["account.journal"].create({
            "name": "Reclass by account", "code": "RECLA",
            "type": "general", "company_id": self.company.id,
        })
        company_journal = self.env["account.journal"].create({
            "name": "Reclass by company", "code": "RECLC",
            "type": "general", "company_id": self.company.id,
        })

        # 1. The account wins over everything.
        self.account_dest.reclass_mirror_journal_id = account_journal
        bill = self._create_bill()
        bill.action_post()
        self.assertEqual(bill.reclass_mirror_move_id.journal_id, account_journal)

        # 2. Without it, the journal of the bill.
        self.account_dest.reclass_mirror_journal_id = False
        bill.action_reclass_generate_mirror()
        self.assertEqual(bill.reclass_mirror_move_id.journal_id, self.mirror_journal)

        # 3. Without it, the company default.
        self.purchase_journal.reclass_mirror_journal_id = False
        self.company.reclass_mirror_journal_id = company_journal
        bill.action_reclass_generate_mirror()
        self.assertEqual(bill.reclass_mirror_move_id.journal_id, company_journal)

        # 4. Nothing configured anywhere: no entry is invented.
        self.company.reclass_mirror_journal_id = False
        with self.assertRaisesRegex(UserError, "No journal available"):
            bill.action_reclass_generate_mirror()
        self.assertFalse(bill.reclass_mirror_move_id)

    def test_18_batch_regeneration_from_list_view(self):
        """The mass action regenerates what applies and skips the rest."""
        applicable = self._create_bill()
        applicable.action_post()
        not_configured = self._create_bill(account=self.account_plain)
        not_configured.action_post()
        draft = self._create_bill()

        action = (applicable | not_configured | draft).action_reclass_generate_mirror_batch()

        self.assertTrue(applicable.reclass_mirror_move_id)
        self.assertFalse(not_configured.reclass_mirror_move_id)
        self.assertFalse(draft.reclass_mirror_move_id)
        self.assertEqual(draft.state, "draft", "The batch never posts anything")
        self.assertEqual(action["params"]["type"], "success")
        self.assertIn("1 reclassification entries generated", action["params"]["message"])
        self.assertIn("2 bills skipped", action["params"]["message"])

    def test_19_batch_skips_locked_periods_without_aborting(self):
        """A locked bill never blocks the regeneration of the others."""
        locked_bill = self._create_bill(date=fields.Date.from_string("2026-01-10"))
        locked_bill.action_post()
        open_bill = self._create_bill(date=fields.Date.from_string("2026-06-10"))
        open_bill.action_post()
        open_bill.reclass_mirror_move_id.button_draft()
        open_bill.reclass_mirror_move_id.button_cancel()
        first_mirror = locked_bill.reclass_mirror_move_id

        self.company.sudo().write({
            "fiscalyear_lock_date": fields.Date.from_string("2026-03-31"),
        })

        action = (locked_bill | open_bill).action_reclass_generate_mirror_batch()

        self.assertEqual(action["params"]["type"], "warning")
        self.assertIn("1 bills skipped: their period is locked",
                      action["params"]["message"])
        self.assertEqual(locked_bill.reclass_mirror_move_id, first_mirror,
                         "The locked bill keeps its entry untouched")
        self.assertEqual(first_mirror.state, "posted")
        self.assertTrue(open_bill.reclass_mirror_move_id)
        self.assertEqual(open_bill.reclass_mirror_move_id.state, "posted")

    @mute_logger("odoo.addons.account_reclassification.models.account_move")
    def test_19b_broken_setup_never_blocks_the_native_posting(self):
        """A mirror that cannot be built lets the bill post natively anyway."""
        other_company = self.setup_other_company()["company"]
        foreign_journal = self.env["account.journal"].create({
            "name": "Other company journal", "code": "OCJ",
            "type": "general", "company_id": other_company.id,
        })
        # Journal of another company: creating the mirror entry cannot work.
        self.account_dest.reclass_mirror_journal_id = foreign_journal
        bill = self._create_bill()

        bill.action_post()

        self.assertEqual(bill.state, "posted", "The bill must post natively")
        self.assertFalse(bill.reclass_mirror_move_id)
        self.assertFalse(self._mirrors_of(bill))
        # And the accountant still gets a hard error on the manual button.
        with self.assertRaises(Exception):
            bill.action_reclass_generate_mirror()

    def test_20_account_setup_is_validated(self):
        """A mode other than 'none' needs two different accounts."""
        with self.assertRaises(ValidationError):
            self.account_plain.reclass_mirror_mode = "always"
        with self.assertRaises(ValidationError):
            self.account_plain.write({
                "reclass_mirror_mode": "always",
                "reclass_target_account_id": self.account_60.id,
                "reclass_counterpart_account_id": self.account_60.id,
            })

    def test_16_analytic_distribution_is_propagated(self):
        """The analytic distribution of the bill line reaches both mirror lines."""
        plan = self.env["account.analytic.plan"].create({"name": "Reclass Plan"})
        analytic_account = self.env["account.analytic.account"].create({
            "name": "Reclass Cost Centre",
            "plan_id": plan.id,
        })
        distribution = {str(analytic_account.id): 100.0}

        bill = self._create_bill(analytic=distribution)
        bill.action_post()

        mirror = bill.reclass_mirror_move_id
        self.assertTrue(mirror)
        for line in mirror.line_ids:
            self.assertEqual(line.analytic_distribution, distribution)
        # Net analytic impact of the reclassification is zero: no double counting.
        analytic_lines = mirror.line_ids.analytic_line_ids
        self.assertTrue(analytic_lines)
        self.assertEqual(sum(analytic_lines.mapped("amount")), 0.0)
