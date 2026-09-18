from odoo.tests import tagged

from odoo.addons.stock_landed_cost_variance.tests.common import RevaluationCommon


@tagged("post_install", "-at_install")
class TestKardexVariance(RevaluationCommon):
    """The Kardex columns must add up to what Odoo says the stock is worth, after every late revaluation."""

    def _ledger(self):
        self.env.invalidate_all()
        moves = self.env["stock.move"].search([("product_id", "=", self.product.id), ("state", "=", "done")])
        return sum(moves.mapped("kardex_value"))

    def test_restated_delivery_carries_the_correction_in_its_value(self):
        po = self.purchase(5, 500)
        self.bill(po)
        so = self.sale(3)
        self.invoice(so)
        out_move = so.picking_ids.move_ids
        self.assertAlmostEqual(out_move.kardex_value, -1500.0, 2)

        self.landed_cost(po, 250)
        out_move.invalidate_recordset()
        self.assertAlmostEqual(out_move.kardex_value, -1650.0, 2, "the delivery at the landed cost")
        self.assertAlmostEqual(out_move.kardex_value_adjustment, 0.0, 2, "folded: nothing on top")
        self.assertAlmostEqual(self._ledger(), 1100.0, 2)
        self.assertAlmostEqual(self._ledger(), self.total_value(), 2, "the ledger and the engine agree")

    def test_negative_stock_discard_is_added_on_the_entry(self):
        po1 = self.purchase(2, 10)
        self.bill(po1)
        self.invoice(self.sale(5))
        po2 = self.purchase(5, 20)
        self.bill(po2)
        receipt = po2.picking_ids.move_ids
        receipt.invalidate_recordset()
        self.assertAlmostEqual(receipt.kardex_value_adjustment, -30.0, 2,
                               "the value Odoo's replay drops is carried by the entry where it happens")
        self.assertAlmostEqual(self._ledger(), self.total_value(), 2)

    def test_untouched_moves_do_not_move(self):
        """The guarantee for databases that already have this module: a move with no recorded variance
        reads exactly as it did before."""
        po = self.purchase(5, 500)
        so = self.sale(3)
        for move in (po.picking_ids.move_ids, so.picking_ids.move_ids):
            self.assertFalse(move.variance_line_ids)
            self.assertAlmostEqual(move.kardex_value_adjustment, 0.0, 2)
            self.assertAlmostEqual(move.kardex_adjusted_qty, 0.0, 2)
            expected = move.value if move.is_in else -move.value
            self.assertAlmostEqual(move.kardex_value, expected, 2)

    def test_adjusted_qty_never_aggregates(self):
        field = self.env["stock.move"]._fields["kardex_adjusted_qty"]
        self.assertFalse(field.aggregator)
        self.assertEqual(self.env["stock.move"]._fields["kardex_qty"].aggregator, "sum")
