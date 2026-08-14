from odoo.addons.stock_move_kardex_qty.hooks import (
    _seed_kardex_columns,
    _seed_kardex_value_column,
)
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
        # A cost so receipts are actually valued (value > 0); without it the
        # native ``value`` is 0 and the *value* assertions cannot tell +/- apart.
        cls.product.standard_price = 10.0

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

    # ------------------------------------------------------------------
    # kardex_value: the native (unsigned) ``value`` signed +in / -out / 0.
    # ------------------------------------------------------------------
    def test_value_incoming_is_positive_native_value(self):
        move = self._do_move(5, self.supplier, self.stock)
        self.assertTrue(move.is_in)
        self.assertGreater(move.value, 0.0, "receipt should be valued")
        self.assertEqual(move.kardex_value, move.value)

    def test_value_outgoing_is_negative_native_value(self):
        self._do_move(5, self.supplier, self.stock)
        move_out = self._do_move(2, self.stock, self.customer)
        self.assertTrue(move_out.is_out)
        # native value is stored unsigned; the Kardex column negates it.
        self.assertGreaterEqual(move_out.value, 0.0)
        self.assertEqual(move_out.kardex_value, -move_out.value)

    def test_value_internal_transfer_is_zero(self):
        self._do_move(5, self.supplier, self.stock)
        move_int = self._do_move(3, self.stock, self.stock2)
        self.assertEqual(move_int.kardex_value, 0.0)

    def test_value_non_done_move_is_zero(self):
        move = self.env["stock.move"].create({
            "product_id": self.product.id,
            "product_uom_qty": 9,
            "product_uom": self.product.uom_id.id,
            "location_id": self.supplier.id,
            "location_dest_id": self.stock.id,
        })
        self.assertNotEqual(move.state, "done")
        self.assertEqual(move.kardex_value, 0.0)

    def test_value_shares_sign_with_qty(self):
        """The two Kardex columns must never disagree on direction."""
        self._do_move(5, self.supplier, self.stock)      # +
        move_out = self._do_move(2, self.stock, self.customer)  # -
        for m in (self.env["stock.move"].search(
                [("product_id", "=", self.product.id), ("state", "=", "done")])):
            if m.kardex_value and m.kardex_qty:
                self.assertEqual(
                    m.kardex_value > 0, m.kardex_qty > 0,
                    "kardex_value and kardex_qty must share their sign")
        self.assertLess(move_out.kardex_value, 0.0)

    def test_value_sum_reconciles_via_read_group(self):
        """kardex_value must totalise as a ledger through _read_group(:sum) --
        the way the list-view column footer aggregates it. Guards the NULL-sum
        gotcha (an all-zero column can otherwise aggregate to False/blank): here
        there ARE valued rows, so the group sum is the net valuation."""
        m_in = self._do_move(5, self.supplier, self.stock)   # +value (5 @ 10)
        m_out = self._do_move(2, self.stock, self.customer)   # -value (2 @ 10)
        self._do_move(3, self.stock, self.stock2)             # 0 (internal)
        expected = m_in.kardex_value + m_out.kardex_value     # 50 + (-20) = 30
        groups = self.env["stock.move"]._read_group(
            [("product_id", "=", self.product.id), ("state", "=", "done")],
            [],
            ["kardex_value:sum"],
        )
        total = groups[0][0]
        self.assertAlmostEqual(total, expected, places=2)
        self.assertAlmostEqual(total, 30.0, places=2,
                               msg="Sum(kardex_value) must equal net valuation")

    def test_value_recomputes_on_revaluation(self):
        """kardex_value depends on ``value`` -> a manual revaluation self-heals
        the signed column without any flow override."""
        move = self._do_move(5, self.supplier, self.stock)
        self.assertEqual(move.kardex_value, move.value)
        move.value_manual = move.value + 100.0
        self.assertEqual(move.value, move.value_manual)
        self.assertEqual(move.kardex_value, move.value,
                         "signed column must track the revalued native value")

    def test_value_sql_seed_matches_orm_compute(self):
        """The bulk SQL seed for kardex_value must reproduce the ORM compute."""
        m_in = self._do_move(5, self.supplier, self.stock)
        m_out = self._do_move(2, self.stock, self.customer)
        m_int = self._do_move(1, self.stock, self.stock2)
        moves = m_in | m_out | m_int
        orm = {m.id: m.kardex_value for m in moves}
        self.assertEqual(orm[m_in.id], m_in.value)
        self.assertEqual(orm[m_out.id], -m_out.value)
        self.assertEqual(orm[m_int.id], 0.0)

        ids = tuple(orm)
        self.env.cr.execute(
            "UPDATE stock_move SET kardex_value = NULL WHERE id IN %s", (ids,))
        self.env.invalidate_all()
        _seed_kardex_columns(self.env)
        self.env.cr.execute(
            "SELECT id, kardex_value FROM stock_move WHERE id IN %s", (ids,))
        seeded = dict(self.env.cr.fetchall())
        for mid, val in orm.items():
            self.assertAlmostEqual(
                seeded[mid], val, places=6,
                msg="SQL seed diverged from ORM compute for kardex_value")

    def test_value_upgrade_seed_fills_only_value(self):
        """The upgrade path (migrations/19.0.3.0.0) uses the value-only seeder:
        it must fill kardex_value exactly like the ORM, and must NOT disturb the
        already-seeded kardex_qty / kardex_uom_id."""
        m_in = self._do_move(5, self.supplier, self.stock)
        m_out = self._do_move(2, self.stock, self.customer)
        moves = m_in | m_out
        orm_val = {m.id: m.kardex_value for m in moves}
        orm_qty = {m.id: m.kardex_qty for m in moves}

        ids = tuple(orm_val)
        # Simulate the post-upgrade state: column present but empty (what
        # _auto_init leaves before the migration runs); qty already seeded.
        self.env.cr.execute(
            "UPDATE stock_move SET kardex_value = NULL WHERE id IN %s", (ids,))
        self.env.invalidate_all()

        covered = _seed_kardex_value_column(self.env)
        self.assertGreater(covered, 0)

        self.env.cr.execute(
            "SELECT id, kardex_value, kardex_qty FROM stock_move "
            "WHERE id IN %s", (ids,))
        rows = {r[0]: (r[1], r[2]) for r in self.env.cr.fetchall()}
        for mid in ids:
            self.assertAlmostEqual(rows[mid][0], orm_val[mid], places=6)
            self.assertAlmostEqual(rows[mid][1], orm_qty[mid], places=6,
                                   msg="value-only seed must not touch qty")

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
        self.assertIn('name="kardex_value"', arch)
        self.assertRegex(arch, r'name="kardex_value"[^>]*\bsum=')
        # green-in / red-out coloring mirrored from the native quantity column.
        self.assertIn("decoration-success", arch)
        self.assertIn("decoration-danger", arch)
        # column footer total (sum) so the whole column totalizes.
        self.assertRegex(arch, r'name="kardex_qty"[^>]*\bsum=')
        # Our three Kardex columns stay together, injected as one block right
        # after the native Quantity (kardex_qty, kardex_uom_id, kardex_value).
        self.assertLess(
            arch.index('name="kardex_qty"'), arch.index('name="kardex_uom_id"'))
        self.assertLess(
            arch.index('name="kardex_uom_id"'), arch.index('name="kardex_value"'))

    def test_sql_seed_matches_orm_compute(self):
        """The install-time bulk SQL seed (hooks._seed_kardex_columns) must
        reproduce _compute_kardex_qty byte for byte. This is what guarantees the
        historical rows filled during installation match what the ORM would
        compute for a new move.

        Build a representative spread of moves (incoming, outgoing, internal,
        UoM-converted, consignment-excluded, non-done), capture the ORM-computed
        values, wipe both stored columns and re-seed via the hook's SQL, then
        compare the raw DB values (read straight from SQL so the ORM does not
        transparently recompute them on access)."""
        partner_other = self.env["res.partner"].create({"name": "Consignor"})
        m_in = self._do_move(5, self.supplier, self.stock)          # +5
        m_out = self._do_move(2, self.stock, self.customer)         # -2
        m_int = self._do_move(1, self.stock, self.stock2)           # 0 internal
        # UoM-converted incoming: 2 dozen -> 24 units (product reference UoM).
        dozen = self.env.ref("uom.product_uom_dozen")
        m_dz = self.env["stock.move"].create({
            "product_id": self.product.id,
            "product_uom_qty": 2,
            "product_uom": dozen.id,
            "location_id": self.supplier.id,
            "location_dest_id": self.stock.id,
        })
        m_dz._action_confirm()
        m_dz._action_assign()
        for ml in m_dz.move_line_ids:
            ml.quantity = 2
            ml.picked = True
        m_dz._action_done()                                        # +24
        # Consignment: the sole line is owned by a third party -> excluded from
        # valuation -> is_in False -> kardex_qty 0 (both ORM and SQL).
        m_cons = self.env["stock.move"].create({
            "product_id": self.product.id,
            "product_uom_qty": 7,
            "product_uom": self.product.uom_id.id,
            "location_id": self.supplier.id,
            "location_dest_id": self.stock.id,
        })
        m_cons._action_confirm()
        m_cons._action_assign()
        for ml in m_cons.move_line_ids:
            ml.quantity = 7
            ml.picked = True
            ml.owner_id = partner_other
        m_cons._action_done()                                      # 0 (excluded)
        # Non-done incoming -> 0.
        m_draft = self.env["stock.move"].create({
            "product_id": self.product.id,
            "product_uom_qty": 9,
            "product_uom": self.product.uom_id.id,
            "location_id": self.supplier.id,
            "location_dest_id": self.stock.id,
        })

        moves = m_in | m_out | m_int | m_dz | m_cons | m_draft
        orm = {m.id: (m.kardex_qty, m.kardex_uom_id.id) for m in moves}
        # Sanity: the fixture actually exercises the distinct branches.
        self.assertEqual(orm[m_in.id][0], 5.0)
        self.assertEqual(orm[m_out.id][0], -2.0)
        self.assertEqual(orm[m_int.id][0], 0.0)
        self.assertEqual(orm[m_dz.id][0], 24.0)
        self.assertEqual(orm[m_cons.id][0], 0.0)
        self.assertEqual(orm[m_draft.id][0], 0.0)

        ids = tuple(orm)
        self.env.cr.execute(
            "UPDATE stock_move SET kardex_qty = NULL, kardex_uom_id = NULL "
            "WHERE id IN %s", (ids,))
        self.env.invalidate_all()

        _seed_kardex_columns(self.env)

        self.env.cr.execute(
            "SELECT id, kardex_qty, kardex_uom_id FROM stock_move "
            "WHERE id IN %s", (ids,))
        seeded = {r[0]: (r[1], r[2]) for r in self.env.cr.fetchall()}

        for mid, (qty, uom_id) in orm.items():
            self.assertAlmostEqual(
                seeded[mid][0], qty, places=6,
                msg="SQL seed diverged from ORM compute for kardex_qty")
            self.assertEqual(
                seeded[mid][1], uom_id,
                "SQL seed diverged from ORM compute for kardex_uom_id")

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
