# Copyright 2026 Ganemo
# License OPL-1 (Odoo Proprietary License v1.0) - See LICENSE file.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestCogsAnalyticFilter(AccountTestInvoicingCommon):
    """The module reimposes a single invariant, consistent with
    ``stock_analytic_distribution``: the COGS line booked on the product's
    stock valuation account (the inventory counterpart) must not keep an
    analytic distribution; every other COGS line (e.g. the expense line) must.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        cls.analytic_plan = cls.env["account.analytic.plan"].create(
            {"name": "Test Plan"}
        )
        cls.analytic_account = cls.env["account.analytic.account"].create(
            {"name": "Test Analytic", "plan_id": cls.analytic_plan.id}
        )
        cls.distribution = {str(cls.analytic_account.id): 100}

        # The product's stock valuation account -> the COGS counterpart that
        # must never carry analytic.
        cls.valuation_account = cls.env["account.account"].create(
            {
                "name": "Stock Valuation (test)",
                "code": "TESTSTKVAL",
                "account_type": "asset_current",
            }
        )
        cls.product_a.categ_id.property_stock_valuation_account_id = (
            cls.valuation_account
        )

        # A Profit & Loss account (expense) -> analytic is legitimate.
        cls.pnl_account = cls.company_data["default_account_expense"]
        # Another balance-sheet account that is NOT the valuation account ->
        # under the new (narrow) criterion it must be left untouched.
        cls.other_bs_account = cls.env["account.account"].create(
            {
                "name": "Other Asset (test)",
                "code": "TESTOTHAS",
                "account_type": "asset_current",
            }
        )

        cls.invoice = cls.init_invoice(
            "out_invoice", products=cls.product_a, post=False
        )

    def _make_cogs_line(self, account):
        """Create a COGS journal item already carrying the analytic
        distribution (as the upstream override would leave it)."""
        return self.env["account.move.line"].create(
            {
                "move_id": self.invoice.id,
                "display_type": "cogs",
                "name": "COGS test",
                "product_id": self.product_a.id,
                "account_id": account.id,
                "analytic_distribution": self.distribution,
            }
        )

    def test_valuation_cogs_line_is_stripped(self):
        line = self._make_cogs_line(self.valuation_account)
        line._compute_analytic_distribution()
        self.assertFalse(
            line.analytic_distribution,
            "Analytic must be cleared on the COGS stock valuation line.",
        )

    def test_pnl_cogs_line_is_kept(self):
        line = self._make_cogs_line(self.pnl_account)
        line._compute_analytic_distribution()
        self.assertEqual(
            line.analytic_distribution,
            self.distribution,
            "Analytic must be preserved on the COGS expense line.",
        )

    def test_other_balance_sheet_cogs_line_is_kept(self):
        # Narrow, consistent criterion: only the stock valuation account is
        # excluded, not every balance-sheet account.
        line = self._make_cogs_line(self.other_bs_account)
        line._compute_analytic_distribution()
        self.assertEqual(
            line.analytic_distribution,
            self.distribution,
            "Only the stock valuation account is excluded, not any asset.",
        )

    def test_disabled_keeps_valuation_line(self):
        self.company.cogs_analytic_exclude_valuation = False
        line = self._make_cogs_line(self.valuation_account)
        line._compute_analytic_distribution()
        self.assertEqual(
            line.analytic_distribution,
            self.distribution,
            "With the setting disabled, the analytic distribution must remain.",
        )

    def test_non_cogs_line_is_untouched(self):
        line = self.env["account.move.line"].create(
            {
                "move_id": self.invoice.id,
                "name": "Regular valuation line",
                "account_id": self.valuation_account.id,
                "analytic_distribution": self.distribution,
            }
        )
        line._compute_analytic_distribution()
        self.assertEqual(
            line.analytic_distribution,
            self.distribution,
            "Non-COGS lines must never be touched by this module.",
        )

    def _buggy_cogs_vals(self):
        """A COGS vals_list as the *affected* Odoo 19 builds produce it: the
        analytic distribution is stamped on BOTH the stock valuation line and
        the expense line (the two then cancel out in the analytic ledger).

        This is the real production input. The local Docker image may run a
        different 19.0 build that already leaves the valuation line clean, so
        we feed the buggy shape explicitly instead of relying on the local
        upstream output -- otherwise the test would pass vacuously and never
        catch the regression (the very gap the project rules warn about).
        """
        common = {
            "move_id": self.invoice.id,
            "display_type": "cogs",
            "product_id": self.product_a.id,
        }
        return [
            dict(common, account_id=self.valuation_account.id,
                 analytic_distribution=dict(self.distribution)),
            dict(common, account_id=self.pnl_account.id,
                 analytic_distribution=dict(self.distribution)),
        ]

    def test_cogs_vals_strip_clears_only_valuation(self):
        """The vals-level override (the real production fix) must clear the
        analytic on the stock valuation line and keep it on the expense line,
        even when upstream stamped both."""
        # product_a's valuation account must resolve to cls.valuation_account.
        self.product_a.is_storable = True
        self.product_a.property_account_expense_id = self.pnl_account

        vals_list = self.invoice._strip_cogs_valuation_analytic(
            self._buggy_cogs_vals()
        )
        by_account = {v["account_id"]: v for v in vals_list}
        self.assertFalse(
            by_account[self.valuation_account.id].get("analytic_distribution"),
            "The valuation COGS line vals must have analytic cleared.",
        )
        self.assertEqual(
            by_account[self.pnl_account.id].get("analytic_distribution"),
            self.distribution,
            "The expense COGS line vals must keep the analytic distribution.",
        )

    def test_cogs_vals_strip_disabled_is_noop(self):
        """With the per-company switch off, even the buggy both-lines input is
        left untouched."""
        self.company.cogs_analytic_exclude_valuation = False
        self.product_a.is_storable = True
        self.product_a.property_account_expense_id = self.pnl_account

        vals_list = self.invoice._strip_cogs_valuation_analytic(
            self._buggy_cogs_vals()
        )
        by_account = {v["account_id"]: v for v in vals_list}
        self.assertEqual(
            by_account[self.valuation_account.id].get("analytic_distribution"),
            self.distribution,
            "Disabled: the valuation line must keep its analytic distribution.",
        )
        self.assertEqual(
            by_account[self.pnl_account.id].get("analytic_distribution"),
            self.distribution,
            "Disabled: the expense line must keep its analytic distribution.",
        )

    def test_realtime_cogs_preparation_runs_clean(self):
        """End-to-end smoke of the real upstream method on this build: it must
        run without error and never leave the valuation line carrying analytic
        (whether the build stamped it -- then we strip it -- or not)."""
        self.product_a.is_storable = True
        self.product_a.categ_id.property_valuation = "real_time"
        self.product_a.categ_id.property_cost_method = "standard"
        self.product_a.standard_price = 100.0
        self.product_a.property_account_expense_id = self.pnl_account
        self.invoice.invoice_line_ids.analytic_distribution = self.distribution

        vals_list = self.invoice._stock_account_prepare_realtime_out_lines_vals()
        self.assertTrue(vals_list, "Upstream must produce COGS vals to test.")
        by_account = {v["account_id"]: v for v in vals_list}
        self.assertFalse(
            by_account.get(self.valuation_account.id, {}).get(
                "analytic_distribution"
            ),
            "The valuation COGS line must never end up carrying analytic.",
        )

    def test_integration_project_context_strips_only_valuation(self):
        """End-to-end of the real trigger: with a project in the context,
        ``sale_project`` stamps the project's analytic distribution on the
        COGS lines (it does not exclude the stock valuation line). Our
        override must then strip only the valuation line and keep the
        expense line -- exercising both overrides together, not the
        predicate in isolation.
        """
        # sudo: we exercise the compute logic, not access control. The test
        # user (an accountant) cannot create projects.
        project = self.env["project.project"].sudo().create(
            {"name": "Project X", "account_id": self.analytic_account.id}
        )
        expected = project._get_analytic_distribution()
        self.assertTrue(
            expected, "The project must yield an analytic distribution."
        )

        aml = self.env["account.move.line"].sudo().with_context(
            project_id=project.id
        )
        valuation_line = aml.create(
            {
                "move_id": self.invoice.id,
                "display_type": "cogs",
                "name": "COGS valuation",
                "product_id": self.product_a.id,
                "account_id": self.valuation_account.id,
            }
        )
        expense_line = aml.create(
            {
                "move_id": self.invoice.id,
                "display_type": "cogs",
                "name": "COGS expense",
                "product_id": self.product_a.id,
                "account_id": self.pnl_account.id,
            }
        )

        self.assertFalse(
            valuation_line.analytic_distribution,
            "sale_project stamped the valuation line; it must be stripped.",
        )
        self.assertEqual(
            expense_line.analytic_distribution,
            expected,
            "The expense line must keep the project's analytic distribution.",
        )
