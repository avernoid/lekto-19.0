# Part of Ganemo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestJournalEntryProfitability(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        # Analytic account in the *project* plan, so it maps to the analytic
        # line ``account_id`` column the panel looks at.
        project_plan = next(iter(cls.env["account.analytic.plan"]._get_all_plans()))
        cls.analytic = cls.env["account.analytic.account"].create(
            {"name": "JE Project AA", "plan_id": project_plan.id}
        )
        cls.project = cls.env["project.project"].create(
            {"name": "JE Project", "account_id": cls.analytic.id}
        )
        # Bare accounts / journal so the tests do not need a chart of accounts.
        cls.acc_expense = cls.env["account.account"].create(
            {"name": "JE Expense", "code": "ZJEEXP", "account_type": "expense"}
        )
        cls.acc_income = cls.env["account.account"].create(
            {"name": "JE Income", "code": "ZJEINC", "account_type": "income"}
        )
        cls.acc_other = cls.env["account.account"].create(
            {"name": "JE Other", "code": "ZJEOTH", "account_type": "liability_current"}
        )
        cls.acc_recv = cls.env["account.account"].create(
            {"name": "JE Recv", "code": "ZJEREC", "account_type": "asset_receivable"}
        )
        cls.journal = cls.env["account.journal"].create(
            {"name": "JE Misc", "code": "ZJEJ", "type": "general"}
        )
        cls.sale_journal = cls.env["account.journal"].create(
            {"name": "JE Sale", "code": "ZJES", "type": "sale"}
        )
        cls.partner = cls.env["res.partner"].create(
            {"name": "JE Customer", "property_account_receivable_id": cls.acc_recv.id}
        )

    def _dist(self):
        return {str(self.analytic.id): 100}

    def _post_manual_entry(self, expense_amount):
        """A plain manual journal entry booking an expense on the analytic account."""
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": self.journal.id,
                "line_ids": [
                    (0, 0, {
                        "name": "Manual cost",
                        "account_id": self.acc_expense.id,
                        "debit": expense_amount,
                        "credit": 0.0,
                        "analytic_distribution": self._dist(),
                    }),
                    (0, 0, {
                        "name": "Counterpart",
                        "account_id": self.acc_other.id,
                        "debit": 0.0,
                        "credit": expense_amount,
                    }),
                ],
            }
        )
        move.action_post()
        return move

    def _cost_section(self):
        items = self.project._get_profitability_items()
        return next(
            (d for d in items["costs"]["data"] if d["id"] == "journal_entry_costs"), None
        )

    def test_manual_entry_appears_as_cost(self):
        self._post_manual_entry(150.0)
        section = self._cost_section()
        self.assertIsNotNone(section, "Manual journal entry must add a cost section")
        self.assertAlmostEqual(section["billed"], -150.0)
        # And it must be reflected in the costs total.
        items = self.project._get_profitability_items()
        self.assertAlmostEqual(items["costs"]["total"]["billed"], -150.0)

    def test_label_exposed(self):
        labels = self.project._get_profitability_labels()
        self.assertEqual(labels.get("journal_entry_costs"), "Other Costs (Journal Entries)")

    def test_non_journal_analytic_excluded(self):
        """A timesheet-style analytic item (no journal item) must be ignored,
        so the module never collides with hr_timesheet's own counting."""
        self.env["account.analytic.line"].create(
            {"name": "Fake timesheet", "account_id": self.analytic.id, "amount": -90.0}
        )
        self.assertIsNone(self._cost_section(), "Analytic items with no journal entry must be excluded")

    def test_customer_invoice_not_double_counted(self):
        """An analytic item from a customer invoice (sale move type) must not be
        picked up by the journal-entry source."""
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "journal_id": self.sale_journal.id,
                "invoice_line_ids": [
                    (0, 0, {
                        "name": "Service",
                        "quantity": 1,
                        "price_unit": 200.0,
                        "account_id": self.acc_income.id,
                        "tax_ids": [(6, 0, [])],
                        "analytic_distribution": self._dist(),
                    })
                ],
            }
        )
        invoice.action_post()
        # The invoice created an analytic item on the project account...
        self.assertTrue(
            self.env["account.analytic.line"].search_count(
                [("account_id", "=", self.analytic.id), ("move_line_id.move_id", "=", invoice.id)]
            )
        )
        # ...but it must NOT show in the journal-entry section.
        self.assertIsNone(self._cost_section())

    def test_no_analytic_account_no_crash(self):
        project = self.env["project.project"].create({"name": "No AA"})
        items = project._get_profitability_items()
        self.assertFalse(
            [d for d in items["costs"]["data"] if d["id"] == "journal_entry_costs"]
        )
