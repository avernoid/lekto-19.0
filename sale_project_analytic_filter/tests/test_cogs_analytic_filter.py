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
