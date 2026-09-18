import logging
import time

from odoo.tests import tagged

from .common import RevaluationCommon

_logger = logging.getLogger(__name__)

EXITS = 300
BUDGET_SECONDS = 120.0


@tagged("post_install", "-at_install")
class TestEnginePerformance(RevaluationCommon):
    """A landed cost on a product with many exits: the engine replays the whole history of the product on
    every event, so this is the cost that grows. It is measured here so a change that makes it quadratic
    shows up as a failed build rather than as a landed cost that takes minutes on a client's database.

    The budget is deliberately loose (a container under load is slower than a laptop); what matters is the
    order of magnitude and the number logged on every run.
    """

    def test_a_landed_cost_over_many_exits(self):
        po = self.purchase(EXITS * 2, 10)
        self.bill(po)
        customers = self.env.ref("stock.stock_location_customers")
        for _index in range(EXITS):
            move = self.env["stock.move"].create({
                "product_id": self.product.id, "product_uom_qty": 1, "product_uom": self.product.uom_id.id,
                "location_id": self.wh.lot_stock_id.id, "location_dest_id": customers.id})
            move._action_confirm()
            move._action_assign()
            move.quantity = 1
            move.picked = True
            move._action_done()

        start = time.time()
        self.landed_cost(po, EXITS * 2)
        elapsed = time.time() - start
        _logger.info("landed cost with %s exits: %.1fs", EXITS, elapsed)

        self.assertKardexInStep()
        self.assertTrue(self.events().identity_ok)
        self.assertLess(elapsed, BUDGET_SECONDS,
                        f"the event took {elapsed:.1f}s over {EXITS} exits: check the replay is not quadratic")
