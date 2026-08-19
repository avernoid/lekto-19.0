from datetime import datetime, timedelta

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

TARGET = datetime(2024, 2, 10, 9, 0, 0)


@tagged("post_install", "-at_install")
class TestStockMoveDateAdjustMrp(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stock_location = cls.env.ref("stock.stock_location_stock")
        cls.finished = cls.env["product.product"].create({
            "name": "Assembled Table", "type": "consu", "is_storable": True,
        })
        cls.comp_a = cls.env["product.product"].create({
            "name": "Table Top", "type": "consu", "is_storable": True,
        })
        cls.comp_b = cls.env["product.product"].create({
            "name": "Table Leg", "type": "consu", "is_storable": True,
        })
        cls.bom = cls.env["mrp.bom"].create({
            "product_tmpl_id": cls.finished.product_tmpl_id.id,
            "product_qty": 1,
            "type": "normal",
            "bom_line_ids": [
                (0, 0, {"product_id": cls.comp_a.id, "product_qty": 1}),
                (0, 0, {"product_id": cls.comp_b.id, "product_qty": 4}),
            ],
        })
        for product, qty in ((cls.comp_a, 20), (cls.comp_b, 80)):
            cls.env["stock.quant"].with_context(inventory_mode=True).create({
                "product_id": product.id,
                "location_id": cls.stock_location.id,
                "inventory_quantity": qty,
            }).action_apply_inventory()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_done_mo(self, qty=1):
        mo = self.env["mrp.production"].create({
            "product_id": self.finished.id,
            "bom_id": self.bom.id,
            "product_qty": qty,
            "product_uom_id": self.finished.uom_id.id,
        })
        mo.action_confirm()
        mo.action_assign()
        mo.qty_producing = qty
        for move in mo.move_raw_ids:
            move.quantity = move.product_uom_qty
            move.picked = True
        res = mo.button_mark_done()
        if isinstance(res, dict) and res.get("res_model"):
            wizard = self.env[res["res_model"]].browse(res.get("res_id"))
            if not wizard:
                wizard = self.env[res["res_model"]].with_context(
                    **res.get("context", {})).create({})
            wizard.action_confirm()
        self.assertEqual(mo.state, "done")
        return mo

    def _wizard(self, moves, **values):
        vals = {"move_ids": [(6, 0, moves.ids)], "reason": "unit test"}
        vals.update(values)
        return self.env["stock.move.date.adjust.wizard"].create(vals)

    # ------------------------------------------------------------------
    # 8 -- manufacturing order, one pass
    # ------------------------------------------------------------------

    def test_08_production_components_and_finished(self):
        mo = self._make_done_mo()
        moves = mo._date_adjust_get_moves()
        self.assertEqual(moves, mo.move_raw_ids | mo.move_finished_ids)

        self._wizard(moves, mode="fixed", new_date=TARGET, stagger=False).action_apply()

        for move in mo.move_raw_ids | mo.move_finished_ids:
            self.assertEqual(move.date, TARGET)
            for line in move.move_line_ids:
                self.assertEqual(line.date, TARGET)

    # ------------------------------------------------------------------
    # 9 -- the force_date context actually travels
    # ------------------------------------------------------------------

    def test_09_done_order_header_is_rewritten(self):
        mo = self._make_done_mo()
        self.assertEqual(mo.state, "done")

        # Proves the guard is real: without the context this raises.
        with self.assertRaises(UserError):
            mo.write({"date_start": TARGET})

        self._wizard(mo._date_adjust_get_moves(), mode="fixed",
                     new_date=TARGET, stagger=False).action_apply()

        self.assertEqual(mo.date_start, TARGET)
        self.assertEqual(mo.date_finished, TARGET)

    # ------------------------------------------------------------------
    # 10 -- staggering
    # ------------------------------------------------------------------

    def test_10_stagger_puts_output_after_components(self):
        mo = self._make_done_mo()

        self._wizard(mo._date_adjust_get_moves(), mode="fixed",
                     new_date=TARGET, stagger=True).action_apply()

        for move in mo.move_raw_ids:
            self.assertEqual(move.date, TARGET)
        for move in mo.move_finished_ids:
            self.assertEqual(move.date, TARGET + timedelta(hours=1))
        self.assertEqual(mo.date_start, TARGET)
        self.assertEqual(mo.date_finished, TARGET + timedelta(hours=1))

    def test_10b_origin_classification(self):
        mo = self._make_done_mo()
        for move in mo.move_raw_ids:
            self.assertEqual(move._date_adjust_origin(), ("production_raw", mo))
            self.assertEqual(move._date_adjust_stagger_rank(), 0)
        for move in mo.move_finished_ids:
            self.assertEqual(move._date_adjust_origin(), ("production_finished", mo))
            self.assertEqual(move._date_adjust_stagger_rank(), 1)

    # ------------------------------------------------------------------
    # 11 -- by-products travel with the finished product
    # ------------------------------------------------------------------

    def test_11_byproducts_are_included(self):
        byproduct = self.env["product.product"].create({
            "name": "Sawdust", "type": "consu", "is_storable": True,
        })
        self.bom.write({
            "byproduct_ids": [(0, 0, {
                "product_id": byproduct.id,
                "product_qty": 1,
                "product_uom_id": byproduct.uom_id.id,
            })],
        })
        mo = self._make_done_mo()
        byproduct_moves = mo.move_finished_ids.filtered(
            lambda m: m.product_id == byproduct)
        self.assertTrue(byproduct_moves, "the by-product move must exist")
        self.assertIn(byproduct_moves, mo._date_adjust_get_moves())

        self._wizard(mo._date_adjust_get_moves(), mode="fixed",
                     new_date=TARGET, stagger=False).action_apply()

        self.assertEqual(byproduct_moves.date, TARGET)

    # ------------------------------------------------------------------
    # 12 -- disassembly
    # ------------------------------------------------------------------

    def test_12_unbuild_both_directions(self):
        mo = self._make_done_mo()
        unbuild = self.env["mrp.unbuild"].create({
            "mo_id": mo.id,
            "product_id": self.finished.id,
            "product_qty": 1,
            "product_uom_id": self.finished.uom_id.id,
        })
        unbuild.action_unbuild()
        self.assertEqual(unbuild.state, "done")

        created_at = unbuild.create_date
        moves = unbuild._date_adjust_get_moves()
        self.assertTrue(moves)
        # The core stamps `unbuild_id` on every movement, consumption included.
        self.assertEqual(moves, unbuild.produce_line_ids)
        self.assertFalse(unbuild.consume_line_ids,
                         "the core never populates consume_unbuild_id")
        self.assertTrue(any(m.is_out for m in moves), "consumption of the product")
        self.assertTrue(any(m.is_in for m in moves), "return of the components")

        self._wizard(moves, mode="fixed", new_date=TARGET, stagger=False).action_apply()

        for move in moves:
            self.assertEqual(move.date, TARGET)
            self.assertEqual(move._date_adjust_origin(), ("unbuild", unbuild))
        self.assertEqual(unbuild.create_date, created_at,
                         "create_date is an audit field and must not be falsified")

    def test_12b_unbuild_stagger_consumes_before_returning(self):
        mo = self._make_done_mo()
        unbuild = self.env["mrp.unbuild"].create({
            "mo_id": mo.id,
            "product_id": self.finished.id,
            "product_qty": 1,
            "product_uom_id": self.finished.uom_id.id,
        })
        unbuild.action_unbuild()
        moves = unbuild._date_adjust_get_moves()

        self._wizard(moves, mode="fixed", new_date=TARGET, stagger=True).action_apply()

        for move in moves.filtered("is_out"):
            self.assertEqual(move.date, TARGET)
        for move in moves.filtered("is_in"):
            self.assertEqual(move.date, TARGET + timedelta(hours=1))

    def test_13_selecting_one_component_pulls_the_whole_order(self):
        """MRP cascades a header date onto every raw move, so say so up front."""
        mo = self._make_done_mo()
        components = mo.move_raw_ids
        self.assertGreater(len(components), 1, "the fixture needs two components")
        picked = components[0]

        wizard = self._wizard(picked, mode="fixed", new_date=TARGET, stagger=False)

        # date_start cascades onto move_raw_ids only; the finished product hangs
        # off date_finished, which nothing here writes. So the components travel
        # together and the output stays put -- which is what the core does.
        self.assertEqual(wizard.effective_move_ids, components,
                         "the sibling components are dragged along")
        self.assertNotIn(mo.move_finished_ids, wizard.effective_move_ids,
                         "the finished product is not touched by date_start")
        self.assertEqual(wizard.sibling_count, len(components) - 1)

        wizard.action_apply()

        for move in components:
            self.assertEqual(move.date, TARGET)
            self.assertTrue(move.date_adjusted, "every moved line must be traceable")
            self.assertTrue(move.original_date)
        self.assertEqual(mo.date_start, TARGET)

    def test_14_note_renders_on_manufacturing_chatters(self):
        """The shared note builder also posts to mrp.production and mrp.unbuild."""
        mo = self._make_done_mo()
        self._wizard(mo._date_adjust_get_moves(), mode="fixed",
                     new_date=TARGET, stagger=False).action_apply()
        self.assertTrue(mo.message_ids)
        body = mo.message_ids[0].body
        self.assertIn("<table", body, "manufacturing order: must render as HTML")
        self.assertNotIn("&lt;", body)

        unbuild = self.env["mrp.unbuild"].create({
            "mo_id": mo.id, "product_id": self.finished.id,
            "product_qty": 1, "product_uom_id": self.finished.uom_id.id,
        })
        unbuild.action_unbuild()
        self._wizard(unbuild._date_adjust_get_moves(), mode="fixed",
                     new_date=TARGET - timedelta(days=1)).action_apply()
        self.assertTrue(unbuild.message_ids)
        body = unbuild.message_ids[0].body
        self.assertIn("<table", body, "disassembly: must render as HTML")
        self.assertNotIn("&lt;", body)

    def test_15_one_order_counts_as_one_document(self):
        """Components and finished product are two origin GROUPS, one document."""
        mo = self._make_done_mo()

        wizard = self._wizard(mo._date_adjust_get_moves(), mode="fixed",
                              new_date=TARGET)

        self.assertGreater(wizard.move_count, 1)
        self.assertEqual(wizard.document_count, 1,
                         "one manufacturing order is one document, not two")
