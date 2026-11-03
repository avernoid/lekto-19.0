from odoo.tests import tagged

from odoo.addons.stock_landed_cost_variance.tests.common import RevaluationCommon


@tagged("post_install", "-at_install")
class TestRebuildDemoData(RevaluationCommon):
    """The demo must leave history that is genuinely uncorrected, and the wizard must fix it.

    If the demo built a product whose values are already right, the rebuild wizard would report zero
    movements and nobody would understand what the module does -- which is the same as having no demo.
    """

    def build(self):
        """As Odoo runs it when loading the demo file: as superuser."""
        self.env["stock.valuation.recalc.audit"].sudo()._valuation_rebuild_build_demo()
        self.env.invalidate_all()

    def demo_product(self):
        return self.env["product.product"].search([("default_code", "=", "TAB-DIST-12")], limit=1)

    def kardex(self, product):
        moves = self.env["stock.move"].search([
            ("product_id", "=", product.id), ("state", "=", "done"),
            "|", ("is_in", "=", True), ("is_out", "=", True)])
        return sum(move.value if move.is_in else -move.value for move in moves)

    def test_the_demo_leaves_history_to_rebuild(self):
        self.build()
        product = self.demo_product()
        self.assertTrue(product, "the demo product must exist")
        inventory = product.with_company(self.company).total_value
        self.assertAlmostEqual(inventory, 1700.0, 2, "2 units at 850, freight included")
        self.assertAlmostEqual(self.kardex(product), 1800.0, 2,
                               "the Kardex is above the inventory: the delivery kept its old cost")
        self.assertFalse(self.env["stock.value.revaluation"].search([("product_id", "=", product.id)]),
                         "the history was built with the engine off, so it left no event")

    def test_the_wizard_puts_that_history_back_in_line(self):
        self.build()
        product = self.demo_product()
        moves = self.env["stock.move"].search([("product_id", "=", product.id), ("state", "=", "done")])
        wizard = self.env["stock.valuation.recalc.wizard"].with_context(
            active_model="stock.move", active_ids=moves.ids).create({})
        action = wizard.action_confirm_recalc()
        self.env.invalidate_all()

        audit = self.env["stock.valuation.recalc.audit"].browse(action["res_id"])
        self.assertEqual(audit.audit_lines.moves_affected_count, 1, "only the delivery changes")
        detail = audit.audit_lines.detail_ids
        self.assertAlmostEqual(detail.previous_value, 1600.0, 2)
        self.assertAlmostEqual(detail.new_value, 1700.0, 2)
        self.assertAlmostEqual(self.kardex(product), product.with_company(self.company).total_value, 2,
                               "Kardex and inventory agree once the history is rebuilt")
