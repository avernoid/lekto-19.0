from odoo.tests import tagged

from odoo.addons.stock_landed_cost_variance.tests.test_variance_capture import (
    TestVarianceCapture,
)


@tagged("post_install", "-at_install")
class TestKardexVariance(TestVarianceCapture):
    """The columns must state what the movement is really worth, and must not
    move for anything that predates the variance record."""

    def test_kardex_value_is_net_of_the_variance(self):
        receipt = self._move("incoming", self.supplier_loc, self.stock_loc, 5.0)
        out = self._move("outgoing", self.stock_loc, self.customer_loc, 3.0)
        in_move = receipt.move_ids
        out_move = out.move_ids

        # Before the landed cost: the column is the plain signed value.
        self.assertAlmostEqual(in_move.kardex_value, 2500.0, 2)
        self.assertAlmostEqual(in_move.kardex_value_adjustment, 0.0, 2)

        self._landed_cost(receipt, 250.0)
        in_move.invalidate_recordset()

        # The core put the whole 250 on the receipt; 150 of it belongs to the
        # 3 units already gone, so the ledger must count 2600, not 2750.
        self.assertAlmostEqual(in_move.value, 2750.0, 2, "native value unchanged")
        self.assertAlmostEqual(in_move.kardex_value_adjustment, -150.0, 2)
        self.assertAlmostEqual(in_move.kardex_value, 2600.0, 2)
        self.assertAlmostEqual(in_move.kardex_adjusted_qty, 3.0, 2)

        # And the ledger now closes on the real value of what is left.
        ledger = in_move.kardex_value + out_move.kardex_value
        self.assertAlmostEqual(ledger, 1100.0, 2, "2 units at the landed 550")
        self.assertAlmostEqual(
            ledger, self.product.with_company(self.company).total_value, 2,
            "the ledger and the valuation engine agree")

    def test_absorbed_variance_stops_counting(self):
        receipt = self._move("incoming", self.supplier_loc, self.stock_loc, 5.0)
        self._move("outgoing", self.stock_loc, self.customer_loc, 3.0)
        self._landed_cost(receipt, 250.0)
        in_move = receipt.move_ids
        variance = self.env["stock.value.variance"].search(
            [("move_id", "=", in_move.id)])

        variance.absorbed = True
        in_move.invalidate_recordset()
        self.assertAlmostEqual(in_move.kardex_value_adjustment, 0.0, 2)
        self.assertAlmostEqual(in_move.kardex_value, 2750.0, 2,
                               "back to gross: a recalculation owns the correction now")

    def test_untouched_moves_do_not_move(self):
        """The guarantee for databases that already have this module: a move
        with no recorded variance reads exactly as it did before."""
        receipt = self._move("incoming", self.supplier_loc, self.stock_loc, 5.0)
        out = self._move("outgoing", self.stock_loc, self.customer_loc, 3.0)
        for move in (receipt.move_ids, out.move_ids):
            self.assertFalse(move.variance_line_ids)
            self.assertAlmostEqual(move.kardex_value_adjustment, 0.0, 2)
            self.assertAlmostEqual(move.kardex_adjusted_qty, 0.0, 2)
            expected = move.value if move.is_in else -move.value
            self.assertAlmostEqual(move.kardex_value, expected, 2)

    def test_adjusted_qty_never_aggregates(self):
        """It counts units that did not move; summing it would corrupt a
        physical count, which is precisely what this module protects."""
        field = self.env["stock.move"]._fields["kardex_adjusted_qty"]
        self.assertFalse(field.aggregator)
        self.assertEqual(
            self.env["stock.move"]._fields["kardex_qty"].aggregator, "sum",
            "the real quantity column still aggregates")
