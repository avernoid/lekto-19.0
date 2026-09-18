from unittest import SkipTest

from odoo import Command
from odoo.modules.registry import Registry
from odoo.tests import get_db_name, tagged

from .common import RevaluationHelpers

try:
    from odoo.addons.point_of_sale.tests.common import TestPoSCommon
except ImportError:  # point_of_sale is not in the addons path
    TestPoSCommon = None


if TestPoSCommon:

    @tagged("post_install", "-at_install")
    class TestEnginePos(RevaluationHelpers, TestPoSCommon):
        """Point of sale (design v4, D5): which part of a late revaluation already has its cost of sales.

        A closed session and an invoiced order have posted it; an open session has not, so its share stays
        in inventory until the session closes and Odoo posts it at the corrected cost. Measured before
        building the engine (valuation_gl_probe, POS scenarios).
        """

        @classmethod
        def setUpClass(cls):
            # The module being in the addons path does not mean it is installed in this database, and the
            # point of sale fixture reads its data: check the registry before the base class touches it.
            if "pos.order" not in Registry(get_db_name()).models:
                raise SkipTest("point_of_sale is not installed")
            super().setUpClass()
            cls._setup_revaluation()
            cls.product.write({"available_in_pos": True, "lst_price": 1000.0, "taxes_id": [Command.clear()]})

        def setUp(self):
            super().setUp()
            self.config = self.basic_config
            self._setup_revaluation_case()

        def pos_sale(self, qty, invoiced=False):
            session = self.open_new_session()
            order = self.create_ui_order_data(
                [(self.product, qty)],
                customer=self.partner_a if invoiced else False, is_invoiced=invoiced,
                payments=[(self.cash_pm1, 1000.0 * qty)])
            self.env["pos.order"].sync_from_ui([order])
            return session

        def close(self, session):
            session.post_closing_cash_details(sum(session.order_ids.payment_ids.mapped("amount")))
            session.close_session_from_ui()

        def test_session_closed_before_the_landed_cost(self):
            po = self.purchase(5, 500)
            self.bill(po)
            self.close(self.pos_sale(3))
            self.landed_cost(po, 250)
            self.assertStockAccountingInStep()
            self.assertKardexInStep()
            self.assertAlmostEqual(self.events().costed_amount, 150.0, 2, "3 units already costed by the session")
            self.assertAlmostEqual(self.balance(self.acc_cogs), 1650.0, 2)

        def test_landed_cost_while_the_session_is_still_open(self):
            po = self.purchase(5, 500)
            self.bill(po)
            session = self.pos_sale(3)
            self.landed_cost(po, 250)
            event = self.events()
            self.assertAlmostEqual(event.costed_amount, 0.0, 2, "nothing costed yet")
            self.assertAlmostEqual(event.pending_amount, 150.0, 2, "it waits in inventory")
            # With the session open, Odoo has posted no cost of sales at all: the stock valuation account
            # still holds the goods that already left. That native gap is exactly the value of the exit,
            # and it closes when the session does -- it is not something this module can post in advance.
            exit_move = self.env["stock.move"].search([("product_id", "=", self.product.id),
                                                       ("state", "=", "done"), ("is_out", "=", True)])
            self.assertAlmostEqual(self.balance(self.acc_valuation) - self.total_value(),
                                   sum(exit_move.mapped("value")), 2)
            self.close(session)
            self.assertStockAccountingInStep()
            self.assertKardexInStep()
            self.assertAlmostEqual(self.balance(self.acc_cogs), 1650.0, 2,
                                   "the session posts the cost of sales at the corrected cost")

        def test_invoiced_order_before_the_landed_cost(self):
            po = self.purchase(5, 500)
            self.bill(po)
            session = self.pos_sale(3, invoiced=True)
            self.close(session)
            self.landed_cost(po, 250)
            self.assertStockAccountingInStep()
            self.assertKardexInStep()
            self.assertAlmostEqual(self.events().costed_amount, 150.0, 2,
                                   "an invoiced order posted its cost of sales")
            self.assertAlmostEqual(self.balance(self.acc_cogs), 1650.0, 2)
