from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestKardexQty(TransactionCase):
    """kardex_qty = signed valued quantity; Sum(in - out) reconciles with
    on-hand; internal/non-done contribute 0; the exposed UoM is the product's
    reference UoM."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stock = cls.env.ref("stock.stock_location_stock")
        cls.supplier = cls.env.ref("stock.stock_location_suppliers")
        cls.customer = cls.env.ref("stock.stock_location_customers")
        cls.stock2 = cls.env["stock.location"].create({
            "name": "Kardex Secondary",
            "usage": "internal",
            "location_id": cls.stock.location_id.id,
        })
        cls.product = cls.env["product.product"].create({
            "name": "Kardex Test Product",
            "type": "consu",
            "is_storable": True,
        })
        cls.product.categ_id.property_cost_method = "average"

    def _do_move(self, qty, src, dst):
        move = self.env["stock.move"].create({
            "product_id": self.product.id,
            "product_uom_qty": qty,
            "product_uom": self.product.uom_id.id,
            "location_id": src.id,
            "location_dest_id": dst.id,
        })
        move._action_confirm()
        move._action_assign()
        for ml in move.move_line_ids:
            ml.quantity = qty
            ml.picked = True
        move._action_done()
        return move

    def test_incoming_is_positive_valued_qty(self):
        move = self._do_move(5, self.supplier, self.stock)
        self.assertTrue(move.is_in)
        self.assertEqual(move.kardex_qty, 5.0)

    def test_outgoing_is_negative_valued_qty(self):
        self._do_move(5, self.supplier, self.stock)
        move_out = self._do_move(2, self.stock, self.customer)
        self.assertTrue(move_out.is_out)
        self.assertEqual(move_out.kardex_qty, -2.0)

    def test_internal_transfer_is_zero(self):
        self._do_move(5, self.supplier, self.stock)
        move_int = self._do_move(3, self.stock, self.stock2)
        self.assertFalse(move_int.is_in)
        self.assertFalse(move_int.is_out)
        self.assertEqual(move_int.kardex_qty, 0.0)

    def test_non_done_move_is_zero(self):
        move = self.env["stock.move"].create({
            "product_id": self.product.id,
            "product_uom_qty": 9,
            "product_uom": self.product.uom_id.id,
            "location_id": self.supplier.id,
            "location_dest_id": self.stock.id,
        })
        self.assertNotEqual(move.state, "done")
        self.assertEqual(move.kardex_qty, 0.0)

    def test_uom_is_product_reference_uom(self):
        move = self._do_move(5, self.supplier, self.stock)
        self.assertEqual(move.kardex_uom_id, self.product.uom_id)

    def test_sum_reconciles_with_on_hand(self):
        self._do_move(5, self.supplier, self.stock)     # +5
        self._do_move(2, self.stock, self.customer)      # -2
        self._do_move(3, self.stock, self.stock2)        # 0 (internal)
        groups = self.env["stock.move"]._read_group(
            [("product_id", "=", self.product.id), ("state", "=", "done")],
            [],
            ["kardex_qty:sum"],
        )
        total = groups[0][0]
        self.assertEqual(total, 3.0, "Sum(kardex_qty) must equal net on-hand qty")

    def test_native_moves_analysis_list_exposes_kardex_columns(self):
        """The inheritance injects the Kardex columns into the native
        stock.view_move_tree and makes the selected native columns optional.
        Guards against a future core rename of the xpath targets (would make the
        Odoo.SH build red)."""
        native = self.env.ref("stock.view_move_tree")
        arch = self.env["stock.move"].get_view(
            view_id=native.id, view_type="list")["arch"]
        self.assertIn('name="kardex_qty"', arch)
        self.assertIn('name="kardex_uom_id"', arch)
        # green-in / red-out coloring mirrored from the native quantity column.
        self.assertIn("decoration-success", arch)
        self.assertIn("decoration-danger", arch)
        # column footer total (sum) so the whole column totalizes.
        self.assertRegex(arch, r'name="kardex_qty"[^>]*\bsum=')

    def test_demo_data_exercises_every_branch(self):
        """The demo moves cover +in, +in-with-UoM-conversion, -out, internal 0
        and a return. Skips cleanly if the DB was built without demo data."""
        product = self.env["product.product"].search(
            [("default_code", "=", "KRDX-DEMO")], limit=1)
        if not product:
            self.skipTest("demo data not loaded")
        moves = self.env["stock.move"].search(
            [("product_id", "=", product.id), ("state", "=", "done")])
        # net on-hand = 10 + 24 - 3 + 0 + 1 = 32 (internal does not change it).
        self.assertEqual(sum(moves.mapped("kardex_qty")), 32.0)
        # 2 Dozen incoming -> 24 units, expressed in the product reference UoM.
        dozen = self.env.ref("uom.product_uom_dozen")
        dz = moves.filtered(lambda m: m.product_uom == dozen)
        self.assertEqual(dz.kardex_qty, 24.0)
        self.assertEqual(dz.kardex_uom_id, product.uom_id)
        # internal transfer contributes exactly 0.
        internal = moves.filtered(
            lambda m: m.location_id.usage == "internal"
            and m.location_dest_id.usage == "internal")
        self.assertTrue(internal)
        self.assertEqual(sum(internal.mapped("kardex_qty")), 0.0)
