from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOperationType(TransactionCase):
    """Move-level SUNAT operation type: heuristic inference, manual-edit
    protection (provenance flag) and the mass-assignment wizard (source x
    policy)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.country_id = cls.env.ref("base.pe")
        cls.stock = cls.env.ref("stock.stock_location_stock")
        cls.supplier = cls.env.ref("stock.stock_location_suppliers")
        cls.customer = cls.env.ref("stock.stock_location_customers")
        cls.inventory_loc = cls.env["stock.location"].create({
            "name": "Op Inventory Loss",
            "usage": "inventory",
        })
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1)
        cls.product = cls.env["product.product"].create({
            "name": "Op Type Product",
            "type": "consu",
            "is_storable": True,
        })

    def _move(self, qty, src, dst, picking_type=None):
        return self.env["stock.move"].create({
            "product_id": self.product.id,
            "product_uom_qty": qty,
            "product_uom": self.product.uom_id.id,
            "location_id": src.id,
            "location_dest_id": dst.id,
            "picking_type_id": picking_type.id if picking_type else False,
        })

    def _do(self, move):
        move._action_confirm()
        move._action_assign()
        for ml in move.move_line_ids:
            ml.quantity = move.product_uom_qty
            ml.picked = True
        move._action_done()
        return move

    # -------------------- heuristic inference --------------------
    def test_infer_incoming_falls_back_to_02(self):
        move = self._do(self._move(
            5, self.supplier, self.stock, self.warehouse.in_type_id))
        self.assertEqual(move.l10n_pe_operation_type, "2")
        self.assertFalse(move.l10n_pe_operation_type_manual)

    def test_infer_outgoing_falls_back_to_01(self):
        self._do(self._move(5, self.supplier, self.stock, self.warehouse.in_type_id))
        move = self._do(self._move(
            2, self.stock, self.customer, self.warehouse.out_type_id))
        self.assertEqual(move.l10n_pe_operation_type, "1")

    def test_infer_inventory_adjustment_28(self):
        self._do(self._move(5, self.supplier, self.stock, self.warehouse.in_type_id))
        move = self._do(self._move(1, self.stock, self.inventory_loc))
        self.assertEqual(move.l10n_pe_operation_type, "28")

    def test_infer_scrap_13(self):
        self._do(self._move(5, self.supplier, self.stock, self.warehouse.in_type_id))
        scrap = self.env["stock.scrap"].create({
            "product_id": self.product.id,
            "product_uom_id": self.product.uom_id.id,
            "scrap_qty": 1.0,
            "location_id": self.stock.id,
        })
        scrap.do_scrap()
        move = scrap.move_ids[:1]
        self.assertTrue(move.scrap_id)
        self.assertEqual(move._l10n_pe_infer_operation_type(), "13")

    # -------------------- provenance gate --------------------
    def test_manual_write_sets_flag(self):
        move = self._move(5, self.supplier, self.stock, self.warehouse.in_type_id)
        move.l10n_pe_operation_type = "7"
        self.assertTrue(move.l10n_pe_operation_type_manual)

    def test_auto_write_keeps_flag_false(self):
        move = self._move(5, self.supplier, self.stock, self.warehouse.in_type_id)
        move.with_context(l10n_pe_op_auto=True).write({
            "l10n_pe_operation_type": "2"})
        self.assertFalse(move.l10n_pe_operation_type_manual)

    def test_auto_never_clobbers_manual(self):
        move = self._do(self._move(
            5, self.supplier, self.stock, self.warehouse.in_type_id))
        move.l10n_pe_operation_type = "7"  # manual
        self.assertTrue(move.l10n_pe_operation_type_manual)
        # force (non-manual) must NOT touch a manual move...
        move._l10n_pe_populate_operation_type(force=True)
        self.assertEqual(move.l10n_pe_operation_type, "7")
        # ...only force_manual overrides it.
        move._l10n_pe_populate_operation_type(force=True, force_manual=True)
        self.assertEqual(move.l10n_pe_operation_type, "2")

    # -------------------- mass wizard --------------------
    def _wizard(self, moves, **vals):
        return self.env["l10n_pe.operation.type.assign"].with_context(
            active_model="stock.move", active_ids=moves.ids,
        ).create(vals)

    def test_wizard_fixed_only_empty_respects_filled(self):
        empty = self._do(self._move(
            5, self.supplier, self.stock, self.warehouse.in_type_id))
        empty.with_context(l10n_pe_op_auto=True).write(
            {"l10n_pe_operation_type": False, "l10n_pe_operation_type_manual": False})
        filled = self._do(self._move(
            3, self.supplier, self.stock, self.warehouse.in_type_id))
        filled.l10n_pe_operation_type = "9"  # manual, pre-existing
        wiz = self._wizard(empty | filled, source="fixed",
                           operation_type="7", policy="only_empty")
        wiz.action_apply()
        self.assertEqual(empty.l10n_pe_operation_type, "7")
        self.assertTrue(empty.l10n_pe_operation_type_manual,
                        "a fixed assignment is deliberate -> manual")
        self.assertEqual(filled.l10n_pe_operation_type, "9",
                         "only_empty must not touch a filled move")

    def test_wizard_overwrite_auto_respects_manual(self):
        auto_move = self._do(self._move(
            5, self.supplier, self.stock, self.warehouse.in_type_id))  # auto '2'
        manual_move = self._do(self._move(
            3, self.supplier, self.stock, self.warehouse.in_type_id))
        manual_move.l10n_pe_operation_type = "9"  # manual
        wiz = self._wizard(auto_move | manual_move, source="fixed",
                           operation_type="7", policy="overwrite_auto")
        wiz.action_apply()
        self.assertEqual(auto_move.l10n_pe_operation_type, "7",
                         "auto-filled move is overwritten")
        self.assertEqual(manual_move.l10n_pe_operation_type, "9",
                         "manual move is respected")

    def test_wizard_overwrite_all_replaces_manual(self):
        manual_move = self._do(self._move(
            3, self.supplier, self.stock, self.warehouse.in_type_id))
        manual_move.l10n_pe_operation_type = "9"
        wiz = self._wizard(manual_move, source="fixed",
                           operation_type="7", policy="overwrite_all")
        wiz.action_apply()
        self.assertEqual(manual_move.l10n_pe_operation_type, "7")

    def test_wizard_auto_source(self):
        move = self._do(self._move(
            5, self.supplier, self.stock, self.warehouse.in_type_id))
        move.with_context(l10n_pe_op_auto=True).write(
            {"l10n_pe_operation_type": False})
        wiz = self._wizard(move, source="auto", policy="only_empty")
        self.assertEqual(wiz.eligible_count, 1)
        wiz.action_apply()
        self.assertEqual(move.l10n_pe_operation_type, "2")
        self.assertFalse(move.l10n_pe_operation_type_manual,
                         "auto source keeps the move non-manual")

    def test_wizard_from_picking_requires_native_field(self):
        if "l10n_pe_operation_type" not in self.env["stock.picking"]._fields:
            self.skipTest("l10n_pe_reports_stock not installed (no picking field)")
        picking = self.env["stock.picking"].create({
            "picking_type_id": self.warehouse.in_type_id.id,
            "location_id": self.supplier.id,
            "location_dest_id": self.stock.id,
        })
        # Write after create so the native compute (depends picking_type_id)
        # cannot clobber the value we want to copy down.
        picking.l10n_pe_operation_type = "18"  # Import
        move = self.env["stock.move"].create({
            "product_id": self.product.id,
            "product_uom_qty": 4,
            "product_uom": self.product.uom_id.id,
            "location_id": self.supplier.id,
            "location_dest_id": self.stock.id,
            "picking_id": picking.id,
            "picking_type_id": self.warehouse.in_type_id.id,
        })
        wiz = self._wizard(move, source="from_picking", policy="only_empty")
        wiz.action_apply()
        self.assertEqual(move.l10n_pe_operation_type, "18")

    # -------------------- view injection --------------------
    def test_moves_analysis_list_exposes_operation_type(self):
        """The inheritance injects the operation type column into the native
        stock.view_move_tree ("Moves Analysis"). Guards against a core rename of
        the xpath target (which would make the Odoo.SH build red)."""
        native = self.env.ref("stock.view_move_tree")
        arch = self.env["stock.move"].get_view(
            view_id=native.id, view_type="list")["arch"]
        self.assertIn('name="l10n_pe_operation_type"', arch)
