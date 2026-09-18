import hashlib
import inspect

from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_pe_reports_lib.models.account_general_ledger import (
    GeneralLedgerCustomHandler as NativeHandler,
)
from odoo.addons.stock_landed_cost_variance.tests.common import RevaluationCommon
from odoo.tests import tagged

# sha256 of the native 3.7 query this module calls with a shifted date and whose rows it rewrites. If Odoo
# changes it (row selection, codes, the date comparison), the shift or the matching by code may no longer
# hold: re-read it, re-measure and only then update this hash.
NATIVE_FINGERPRINT = "5b3e6c05f694ce6b66dc69e425a0eeef668e65bbe6565f2efabbf98ba6b81566"

DRIFT = ("Odoo changed l10n_pe_reports_lib._l10n_pe_get_lib_3_7_data, which this module calls and rewrites. "
         "Check the row selection and the date cut before deploying.")


@tagged("post_install", "post_install_l10n", "-at_install")
class TestPle37Consistency(RevaluationCommon):
    """The three numbers a Peruvian accountant reconciles at the close must be the same one: the PLE 13.1
    closing, the PLE 3.7 and the stock valuation account.

    They are produced by three different paths -- the Kardex from the movements, the 3.7 from a SQL query,
    the account from journal entries -- so each module tests its own. This test is the one that checks
    they agree, and it runs whenever the 13.1 bridge is installed as well.
    """

    @classmethod
    @AccountTestInvoicingCommon.setup_chart_template("pe")
    def setUpClass(cls):
        super().setUpClass()
        cls.company.vat = "20557912879"
        cls.env["account.journal"].search([
            ("company_id", "=", cls.company.id), ("type", "in", ("sale", "purchase")),
        ]).write({"l10n_latam_use_documents": False})
        cls.product.write({"default_code": "KA1", "l10n_pe_type_of_existence": "1"})

    def test_native_source_fingerprint(self):
        actual = hashlib.sha256(
            inspect.getsource(NativeHandler._l10n_pe_get_lib_3_7_data).encode()).hexdigest()
        if NATIVE_FINGERPRINT == "BOOTSTRAP":
            self.fail("FINGERPRINT actual=%s" % actual)
        self.assertEqual(actual, NATIVE_FINGERPRINT, DRIFT)

    def ple37(self, date_to):
        self.env.flush_all()
        self.env.invalidate_all()
        handler = self.env["account.general.ledger.report.handler"].with_company(self.company)
        rows = handler._l10n_pe_get_lib_3_7_data(
            {"date": {"date_to": fields.Date.to_string(date_to)}, "companies": [{"id": self.company.id}]}, None)
        return sum(float(row["stock_value"]) for row in rows if row["product_default_code"] == "KA1")

    def ple131_closing(self, period):
        wizard = self.env["l10n_pe.stock.ple.wizard"].with_company(self.company).create(
            {"date_from": period[0], "date_to": period[1]})
        rows = [line.split("|") for line in (wizard._get_ple_report_content("1301") or "").splitlines()]
        ours = [row for row in rows if row[6] == "KA1"]
        return float(ours[-1][-3]) if ours else 0.0

    def test_the_kardex_the_book_and_the_account_say_the_same(self):
        if "l10n_pe.stock.ple.wizard" not in self.env:
            self.skipTest("l10n_pe_reports_stock_transfer_document is not installed")
        self.set_periods()
        po = self.purchase(5, 500, day=self.day(self.p1, 3))
        self.bill(po, day=self.day(self.p1, 3))
        self.invoice(self.sale(3, day=self.day(self.p1, 10)), day=self.day(self.p1, 10))

        for period in (self.p1, self.p2):
            with self.subTest(period=period):
                self.assertAlmostEqual(self.ple131_closing(period), self.ple37(period[1]), 2,
                                       "PLE 13.1 closing and PLE 3.7 must agree")
                self.assertAlmostEqual(self.ple37(period[1]), self.balance(self.acc_valuation, period[1]), 2,
                                       "the book and the stock valuation account must agree")

        # A freight in the next period: each report must move in the same way, and only in that period.
        self.landed_cost(po, 250, day=self.day(self.p2, 5))
        self.assertAlmostEqual(self.ple131_closing(self.p1), self.ple37(self.p1[1]), 2)
        self.assertAlmostEqual(self.ple37(self.p1[1]), 1000.0, 2, "P1 keeps what it was filed with")
        self.assertAlmostEqual(self.ple131_closing(self.p2), self.ple37(self.p2[1]), 2)
        self.assertAlmostEqual(self.ple37(self.p2[1]), self.balance(self.acc_valuation, self.p2[1]), 2)
        self.assertAlmostEqual(self.ple37(self.p2[1]), self.total_value(), 2)
