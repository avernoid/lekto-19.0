from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.stock_landed_cost_variance.tests.common import RevaluationCommon
from odoo.tests import tagged


@tagged("post_install", "post_install_l10n", "-at_install")
class TestPle37KnownAt(RevaluationCommon):
    """Book 3.7 as known at the end of each period (design v4, D7); figures measured with the prototype."""

    @classmethod
    @AccountTestInvoicingCommon.setup_chart_template("pe")
    def setUpClass(cls):
        super().setUpClass()
        cls.company.vat = "20557912879"
        cls.env["account.journal"].search([
            ("company_id", "=", cls.company.id), ("type", "in", ("sale", "purchase")),
        ]).write({"l10n_latam_use_documents": False})
        cls.product.write({"default_code": "KA-1", "l10n_pe_type_of_existence": "1"})

    def setUp(self):
        super().setUp()
        self.set_periods()

    def ple37(self, date_to):
        self.env.flush_all()
        self.env.invalidate_all()
        handler = self.env["account.general.ledger.report.handler"].with_company(self.company)
        rows = handler._l10n_pe_get_lib_3_7_data(
            {"date": {"date_to": fields.Date.to_string(date_to)}, "companies": [{"id": self.company.id}]}, None)
        ours = [row for row in rows if row["product_default_code"] == "KA1"]
        self.assertLessEqual(len(ours), 1)
        return ours[0] if ours else None

    def test_a_past_period_keeps_the_value_it_was_filed_with(self):
        po = self.purchase(5, 500, day=self.day(self.p1, 3))
        self.bill(po, day=self.day(self.p1, 3))
        self.invoice(self.sale(3, day=self.day(self.p1, 10)), day=self.day(self.p1, 10))
        before = self.ple37(self.p1[1])
        self.assertEqual(before["stock_value"], "1000.00")

        self.landed_cost(po, 250, day=self.day(self.p2, 5))
        after = self.ple37(self.p1[1])
        self.assertEqual(after, before, "the freight of P2 does not enter the 3.7 of P1")
        stored = sum(m.value if m.is_in else -m.value for m in (po.picking_ids | self.env["stock.picking"].search(
            [("sale_id", "!=", False), ("move_ids.product_id", "=", self.product.id)])).move_ids)
        self.assertAlmostEqual(stored, 1100.0, 2, "what the native 3.7 would print: the stored values")

        p2 = self.ple37(self.p2[1])
        self.assertEqual(p2["stock_value"], "1100.00")
        self.assertEqual(p2["stock_unit_cost"], "550.00")
        self.assertAlmostEqual(float(p2["stock_value"]), self.balance(self.acc_valuation, self.p2[1]), 2,
                               "3.7 == stock valuation account at the end of P2")

    def test_movements_of_the_last_day_are_included(self):
        po = self.purchase(5, 500, day=self.day(self.p1, 3))
        self.bill(po, day=self.day(self.p1, 3))
        self.invoice(self.sale(2, day=self.p1[1]), day=self.p1[1])
        row = self.ple37(self.p1[1])
        self.assertEqual(row["stock_quantity"], "3.00", "the delivery of the last day is part of the balance")
        self.assertEqual(row["stock_value"], "1500.00")
        self.assertEqual(row["report_date"], fields.Date.to_string(self.p1[1]).replace("-", ""))

    def test_a_product_sold_out_has_no_row(self):
        po = self.purchase(2, 100, day=self.day(self.p1, 3))
        self.bill(po, day=self.day(self.p1, 3))
        self.invoice(self.sale(2, day=self.day(self.p1, 10)), day=self.day(self.p1, 10))
        self.assertIsNone(self.ple37(self.p1[1]))
