from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged

from . import test_engine_average


@tagged("post_install", "post_install_l10n", "-at_install")
class TestEngineAveragePeruvianChart(test_engine_average.TestEngineAverage):
    """Every average-cost scenario again, on the Peruvian chart of accounts.

    It matters because the measurements were taken on both charts: Peru is not Anglo-Saxon, the cost of
    sales account of the category is a 69xxxx and the stock valuation a 20xxxx, and the accounts of the
    entry come from that configuration. The scenarios are inherited, not copied, so a new case is
    protected on both charts at once.
    """

    allow_inherited_tests_method = True

    @classmethod
    @AccountTestInvoicingCommon.setup_chart_template("pe")
    def setUpClass(cls):
        super().setUpClass()
        cls.company.vat = "20557912879"
        # Peruvian journals ask for a fiscal document on every invoice; the fixture posts plain ones.
        cls.env["account.journal"].search([
            ("company_id", "=", cls.company.id), ("type", "in", ("sale", "purchase")),
        ]).write({"l10n_latam_use_documents": False})
