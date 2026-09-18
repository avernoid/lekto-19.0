from odoo.tests import tagged

from .common import RevaluationCommon
from . import test_engine_methods


class ParityMixin:
    """The replay must give every exit exactly what Odoo's own engine stored when it was validated.

    The engine runs with ``variance_skip_engine`` so nothing is folded: the stored values are Odoo's alone.
    Moves are validated one after another without redating, so several share the same second -- the case
    that broke the per-date native calls -- and (date, id) is the only order that tells them apart.
    """

    def setUp(self):
        super().setUp()
        self.env = self.env(context=dict(self.env.context, variance_skip_engine=True))

    def assertReplayMatchesNative(self, product=None):
        product = (product or self.product).with_company(self.company)
        self.env.invalidate_all()
        Move = self.env["stock.move"].with_company(self.company)
        costs, dropped = Move._variance_replay(product)
        moves = Move.search([("product_id", "=", product.id), ("state", "=", "done"),
                             "|", ("is_in", "=", True), ("is_out", "=", True)])
        self.assertEqual(set(costs), set(moves.filtered("is_out").ids), "every exit is replayed")
        for move in moves.filtered("is_out"):
            self.assertAlmostEqual(costs[move.id], move.value, 2, f"exit {move.id} differs from Odoo's value")
        ledger = sum(m.value if m.is_in else -m.value for m in moves)
        self.assertAlmostEqual(ledger - sum(dropped.values()), product.total_value, 2,
                               "stored values minus what the replay drops == Odoo's inventory value")
        return costs, dropped


@tagged("post_install", "-at_install")
class TestParityAverage(ParityMixin, RevaluationCommon):

    def test_average_with_negative_stock(self):
        self.purchase(5, 10)
        self.sale(3)
        self.purchase(4, 20)
        self.sale(5)
        self.sale(3)
        self.purchase(5, 30)
        self.sale(2)
        _costs, dropped = self.assertReplayMatchesNative()
        self.assertTrue(dropped, "the receipt on negative stock drops value")


@tagged("post_install", "-at_install")
class TestParityFifo(ParityMixin, RevaluationCommon):
    COST_METHOD = "fifo"

    def test_fifo_same_second(self):
        self.purchase(5, 10)
        self.purchase(5, 20)
        self.sale(3)
        self.sale(4)
        self.purchase(2, 40)
        self.sale(4)
        self.assertReplayMatchesNative()

    def test_fifo_with_negative_stock(self):
        self.purchase(2, 10)
        self.sale(5)
        self.purchase(5, 20)
        self.sale(1)
        self.assertReplayMatchesNative()


@tagged("post_install", "-at_install")
class TestParityLots(ParityMixin, test_engine_methods.TestEngineLots):
    # Imported through its module so the loader does not collect TestEngineLots twice; its own test
    # methods are not inherited either (Odoo 19 skips inherited test methods).

    def test_average_lots(self):
        self.set_periods()
        self.buy_lot(5, 500, self.day(self.p1, 3), "L1")
        self.buy_lot(5, 600, self.day(self.p1, 4), "L2")
        self.buy_lot(5, 700, self.day(self.p1, 5), "L1")
        self.sell_lot(3, self.day(self.p1, 10), "L1")
        self.sell_lot(4, self.day(self.p1, 11), "L2")
        self.assertReplayMatchesNative()

    def test_fifo_lots(self):
        self.categ.with_company(self.company).property_cost_method = "fifo"
        self.set_periods()
        self.buy_lot(5, 500, self.day(self.p1, 3), "L1")
        self.buy_lot(5, 600, self.day(self.p1, 4), "L2")
        self.sell_lot(3, self.day(self.p1, 10), "L1")
        self.buy_lot(5, 700, self.day(self.p1, 12), "L1")
        self.sell_lot(4, self.day(self.p1, 13), "L1")
        _costs, dropped = self.assertReplayMatchesNative()
        self.assertAlmostEqual(sum(dropped.values()), -171.43, 2, "exit at the stack average, lot at FIFO")
