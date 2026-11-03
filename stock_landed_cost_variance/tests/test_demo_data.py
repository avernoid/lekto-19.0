from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestDemoData(AccountTestInvoicingCommon):
    """The demo data must show the three situations the module exists for.

    It is built by calling the builder directly, so the test does not depend on the database having
    been created with demo data. A demo that silently builds only part of what it promises is worse
    than no demo: whoever opens the instance concludes the module does nothing in that case.
    """

    def build(self):
        """As Odoo runs it when loading the demo file: as superuser, not as the test's user."""
        self.env["stock.value.revaluation"].sudo()._variance_build_demo()
        self.env.invalidate_all()

    def test_the_three_situations_are_visible(self):
        self.build()
        events = self.env["stock.value.revaluation"].search([])
        by_origin = {event.origin: event for event in events}
        self.assertEqual(set(by_origin), {"landed_cost", "vendor_bill", "negative_stock"},
                         "each demo scenario leaves its own event")

        freight = by_origin["landed_cost"]
        self.assertEqual(freight.product_id.default_code, "CAB-NYY-2X4-100")
        self.assertAlmostEqual(freight.revaluation_amount, 250.0, 2)
        self.assertAlmostEqual(freight.costed_amount, 150.0, 2, "3 of the 5 rolls were already sold")
        self.assertEqual(freight.account_move_id.state, "posted")

        bill = by_origin["vendor_bill"]
        self.assertEqual(bill.product_id.default_code, "LUM-VIAL-150")
        self.assertAlmostEqual(bill.revaluation_amount, -300.0, 2, "5 luminaires at 60 less")
        self.assertAlmostEqual(bill.costed_amount, -180.0, 2, "the 3 sold ones")

        dropped = by_origin["negative_stock"]
        self.assertEqual(dropped.product_id.default_code, "FIJ-PH-12X3")
        self.assertAlmostEqual(dropped.discard_amount, 30.0, 2,
                               "the value Odoo's engine drops when goods arrive on negative stock")

    def test_running_it_twice_builds_nothing_new(self):
        """A module update re-runs the demo file; it must not duplicate anything."""
        Revaluation = self.env["stock.value.revaluation"]
        self.build()
        before = Revaluation.search_count([])
        self.build()
        self.assertEqual(Revaluation.search_count([]), before)
