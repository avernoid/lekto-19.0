from unittest import SkipTest
from unittest.mock import patch

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged

try:
    from odoo.addons.stock_landed_cost_variance.tests.common import RevaluationCommon
except ImportError:  # the engine is an optional companion
    RevaluationCommon = None


if RevaluationCommon:

    @tagged("post_install", "post_install_l10n", "-at_install")
    class TestPleKnownAtPeriods(RevaluationCommon):
        """The PLE 13.1 with late revaluations, on the real TXT (design v4, D7).

        For every period, after every event:
          F1 a period generated before ("filed") regenerates byte-identical;
          F2 its opening is the closing of the previous period;
          F3 its closing is the value known at the end of the period;
          F4 every late amount prints in the period of its event, with its date.

        The scenarios and figures are the ones measured with the prototype before
        this was built (valuation_gl_probe, test_ple_known_at_probe).
        """

        CODE = "KA1"

        @classmethod
        @AccountTestInvoicingCommon.setup_chart_template("pe")
        def setUpClass(cls):
            super().setUpClass()
            if "stock.value.revaluation" not in cls.env:
                raise SkipTest("stock_landed_cost_variance is not installed")
            cls.company.vat = "20557912879"
            cls.env["account.journal"].search([
                ("company_id", "=", cls.company.id), ("type", "in", ("sale", "purchase")),
            ]).write({"l10n_latam_use_documents": False})
            cls.product.write({"default_code": cls.CODE, "l10n_pe_type_of_existence": "1"})

        # ------------------------------------------------------------------ reading the TXT
        def _txt(self, period):
            self.env.flush_all()
            self.env.invalidate_all()
            wizard = self.env["l10n_pe.stock.ple.wizard"].with_company(self.company).create(
                {"date_from": period[0], "date_to": period[1]})
            return wizard._get_ple_report_content("1301") or ""

        def _rows(self, txt):
            rows = []
            for line in txt.splitlines():
                fields_ = line.split("|")
                if fields_[6] != self.CODE:
                    continue
                rows.append({"cuo": fields_[1], "date": fields_[9], "op": fields_[13],
                             "value": float(fields_[-3]), "line": line})
            return rows

        def check_periods(self, file=None, ignore_document=False):
            """F1-F3 over P1..P3; returns the rows per period for F4.

            ``ignore_document`` blanks the serie and number (fields 12 and 13) before comparing a filed
            period: a bill posted after the period changes the document the native report derives for
            the receipt -- measured, native, and not a value.
            """
            result = {}
            previous_close = None
            for name, period in (("P1", self.p1), ("P2", self.p2), ("P3", self.p3)):
                txt = self._txt(period)
                rows = self._rows(txt)
                result[name] = rows
                if name in self.filed:
                    filed, now = self.filed[name], txt
                    if ignore_document:
                        filed, now = self._without_document(filed), self._without_document(now)
                    self.assertEqual(filed, now, f"{name} was filed and must regenerate identically")
                opening = next((r["value"] for r in rows if r["cuo"].endswith("A1")), None)
                if previous_close is not None and opening is not None:
                    self.assertAlmostEqual(opening, previous_close, 2, f"{name} opens where the previous closed")
                closing = rows[-1]["value"] if rows else previous_close or 0.0
                self.assertAlmostEqual(closing, self.known_at(period[1]), 2,
                                       f"{name} closes on the value known at its end")
                previous_close = closing
                if name == file:
                    self.filed[name] = txt
            return result

        def _without_document(self, txt):
            lines = []
            for line in txt.splitlines():
                fields_ = line.split("|")
                fields_[11] = fields_[12] = ""
                lines.append("|".join(fields_))
            return "\n".join(lines)

        def setUp(self):
            super().setUp()
            self.set_periods()
            self.filed = {}

        # ------------------------------------------------------------------ scenarios
        def test_landed_cost_in_the_next_period_then_more(self):
            po = self.purchase(5, 500, day=self.day(self.p1, 3))
            self.bill(po, day=self.day(self.p1, 3))
            self.invoice(self.sale(3, day=self.day(self.p1, 10)), day=self.day(self.p1, 10))
            self.check_periods(file="P1")

            self.landed_cost(po, 250, day=self.day(self.p2, 5))
            rows = self.check_periods(file="P2")
            self.assertAlmostEqual(rows["P1"][-1]["value"], 1000.0, 2, "P1 as filed: 2 units at 500")
            self.assertAlmostEqual(rows["P2"][-1]["value"], 1100.0, 2)
            p2_dates = {r["date"] for r in rows["P2"] if not r["cuo"].endswith("A1")}
            self.assertEqual(p2_dates, {self.day(self.p2, 5).strftime("%d/%m/%Y")},
                             "the landed cost and the restated exit print in P2, on the event date")
            self.assertEqual(sorted(r["op"] for r in rows["P2"] if not r["cuo"].endswith("A1")), ["26", "99"])

            self.invoice(self.sale(1, day=self.day(self.p3, 3)), day=self.day(self.p3, 3))
            self.landed_cost(po, 100, day=self.day(self.p3, 8))
            rows = self.check_periods()
            self.assertAlmostEqual(rows["P3"][-1]["value"], self.total_value(), 2)
            self.assertAlmostEqual(self.balance(self.acc_valuation), self.total_value(), 2)

        def test_late_bill_at_another_price(self):
            po = self.purchase(5, 500, day=self.day(self.p1, 3))
            self.invoice(self.sale(3, day=self.day(self.p1, 10)), day=self.day(self.p1, 10))
            self.check_periods(file="P1")
            self.bill(po, price=560, day=self.day(self.p2, 5))
            rows = self.check_periods(ignore_document=True)
            self.assertAlmostEqual(rows["P2"][-1]["value"], self.total_value(), 2)
            self.assertAlmostEqual(rows["P2"][-1]["value"], 1120.0, 2)

        def test_landed_cost_on_the_consumed_receipt(self):
            po_a = self.purchase(100, 10, day=self.day(self.p1, 3))
            self.bill(po_a, day=self.day(self.p1, 3))
            po_b = self.purchase(100, 10, day=self.day(self.p1, 5))
            self.bill(po_b, day=self.day(self.p1, 5))
            self.invoice(self.sale(100, day=self.day(self.p1, 10)), day=self.day(self.p1, 10))
            self.check_periods(file="P1")
            self.landed_cost(po_a, 100, day=self.day(self.p2, 5))
            rows = self.check_periods()
            self.assertAlmostEqual(rows["P2"][-1]["value"], self.total_value(), 2)

        def test_return_of_an_earlier_sale(self):
            po = self.purchase(5, 500, day=self.day(self.p1, 3))
            self.bill(po, day=self.day(self.p1, 3))
            so = self.sale(3, day=self.day(self.p1, 10))
            invoice = self.invoice(so, day=self.day(self.p1, 10))
            self.check_periods(file="P1")
            self.landed_cost(po, 250, day=self.day(self.p2, 5))
            self.check_periods(file="P2")
            self.return_goods(so, 1, day=self.day(self.p3, 4))
            self.refund(invoice, 1, day=self.day(self.p3, 4))
            rows = self.check_periods()
            self.assertAlmostEqual(rows["P3"][-1]["value"], self.total_value(), 2)

        def test_value_dropped_on_negative_stock_prints_in_its_period(self):
            po1 = self.purchase(2, 10, day=self.day(self.p1, 3))
            self.bill(po1, day=self.day(self.p1, 3))
            self.invoice(self.sale(5, day=self.day(self.p1, 10)), day=self.day(self.p1, 10))
            self.check_periods(file="P1")
            po2 = self.purchase(5, 20, day=self.day(self.p2, 5))
            self.bill(po2, day=self.day(self.p2, 5))
            rows = self.check_periods()
            # The receipt is validated today and redated into P2, so the engine dates the dropped value
            # today: it is known in P3 and prints there, on its own line.
            self.assertNotIn("99", [r["op"] for r in rows["P2"]])
            self.assertIn("99", [r["op"] for r in rows["P3"]], "the dropped value has its own line")
            self.assertAlmostEqual(rows["P3"][-1]["value"], self.total_value(), 2)

        def test_without_late_events_the_file_is_the_native_one(self):
            """Guarantee for databases without late revaluations: the date rule changes nothing."""
            po = self.purchase(5, 500, day=self.day(self.p1, 3))
            self.bill(po, day=self.day(self.p1, 3))
            self.invoice(self.sale(3, day=self.day(self.p1, 10)), day=self.day(self.p1, 10))
            wizard = self.env["l10n_pe.stock.ple.wizard"].with_company(self.company).create(
                {"date_from": self.p1[0], "date_to": self.p1[1]})
            ours = wizard._get_ple_report_content("1301")
            with patch.object(type(wizard), "_l10n_pe_known_at_enabled", lambda self: False):
                without = wizard._get_ple_report_content("1301")
            self.assertTrue(self._rows(ours))
            self.assertEqual(ours, without)
