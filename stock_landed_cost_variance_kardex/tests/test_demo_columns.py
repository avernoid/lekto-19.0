from odoo.tests import tagged

from odoo.addons.stock_landed_cost_variance.tests.common import RevaluationCommon


@tagged("post_install", "-at_install")
class TestKardexColumnsOnDemoData(RevaluationCommon):
    """The bridge has no demo of its own: it shows its worth on the engine's.

    The engine's demo leaves a receipt carrying 30 that no stored value can hold -- the value Odoo's
    average replay drops when goods arrive on negative stock. That is exactly what these columns
    exist to add, so this is where it has to be visible.
    """

    def test_the_adjustment_column_shows_the_dropped_value(self):
        self.env["stock.value.revaluation"].sudo()._variance_build_demo()
        self.env.invalidate_all()

        bolts = self.env["product.product"].search([("default_code", "=", "FIJ-PH-12X3")], limit=1)
        self.assertTrue(bolts, "the engine's demo must have built the negative stock scenario")
        receipts = self.env["stock.move"].search([
            ("product_id", "=", bolts.id), ("state", "=", "done"), ("is_in", "=", True)])
        adjustment = sum(receipts.mapped("kardex_value_adjustment"))
        self.assertAlmostEqual(adjustment, -30.0, 2,
                               "the second receipt carries the value the engine drops")

        moves = self.env["stock.move"].search([
            ("product_id", "=", bolts.id), ("state", "=", "done"),
            "|", ("is_in", "=", True), ("is_out", "=", True)])
        self.assertAlmostEqual(sum(moves.mapped("kardex_value")),
                               bolts.with_company(self.company).total_value, 2,
                               "with the columns, the Kardex adds up to the inventory value")
