from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.stock_account.tests.common import TestStockValuationCommon


@tagged("post_install", "-at_install")
class TestReclassificationProduction(TestStockValuationCommon):
    """The native production/consumption entry, with the counterpart account
    resolved as category -> parent -> grandparent -> native location account."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.production_location = cls.env["stock.location"].search([
            ("usage", "=", "production"),
            ("company_id", "=", cls.company.id),
        ], limit=1)
        cls.account_location = cls.env["account.account"].create({
            "name": "Native production location account",
            "code": "RECLLOC",
            "account_type": "expense",
        })
        cls.production_location.valuation_account_id = cls.account_location
        cls.account_61211 = cls.env["account.account"].create({
            "name": "Reclass 61211 Raw Material Variation",
            "code": "RECL61211",
            "account_type": "expense",
        })
        cls.account_60211 = cls.env["account.account"].create({
            "name": "Reclass 60211 Raw Material Purchases",
            "code": "RECL60211",
            "account_type": "expense",
        })

        # Perpetual (real_time) product, otherwise no native entry is created.
        cls.product = cls.product_avco_auto
        cls.category = cls.product.categ_id
        cls.stock_valuation_account = cls.product._get_product_accounts()["stock_valuation"]

    def _consume_into_production(self, quantity=2.0):
        """Stock -> production location, the native consumption move."""
        self._make_in_move(self.product, 10.0, unit_cost=10.0)
        return self._make_out_move(
            self.product, quantity, location_dest_id=self.production_location.id)

    def _counterpart_lines(self, move):
        """Lines of the native entry that are not the stock valuation side."""
        self.assertTrue(move.account_move_id, "The native entry should exist")
        return move.account_move_id.line_ids.filtered(
            lambda l: l.account_id != self.stock_valuation_account)

    # -------------------------------------------------------------------------
    # PRIORITY 3 -- NATIVE UNTOUCHED
    # -------------------------------------------------------------------------

    def test_01_no_category_account_keeps_native_location_account(self):
        """No account on any category -> the native location account stands."""
        self.assertFalse(self.category._reclass_get_production_account())

        move = self._consume_into_production()

        counterpart = self._counterpart_lines(move)
        self.assertEqual(counterpart.account_id, self.account_location)
        self.assertEqual(len(move.account_move_id.line_ids), 2)
        self.assertEqual(sum(move.account_move_id.line_ids.mapped("balance")), 0.0)

    def test_02_no_account_anywhere_creates_no_entry(self):
        """Neither location nor category: native silence is preserved."""
        self.production_location.valuation_account_id = False

        move = self._consume_into_production()

        self.assertFalse(
            move.account_move_id,
            "With no account at all there is nothing to book, exactly like native")

    def test_02b_category_account_rescues_the_entry(self):
        """No account on the location: the category account saves the entry."""
        self.production_location.valuation_account_id = False
        self.category.reclass_production_account_id = self.account_61211

        move = self._consume_into_production()

        self.assertTrue(
            move.account_move_id,
            "Natively this movement would go unrecorded; the category account "
            "must be found before Odoo decides not to create the entry")
        self.assertRecordValues(
            move.account_move_id.line_ids.sorted(lambda l: l.debit, reverse=True),
            [
                {"account_id": self.account_61211.id, "debit": 20.0, "credit": 0.0},
                {"account_id": self.stock_valuation_account.id, "debit": 0.0, "credit": 20.0},
            ],
        )

    def test_02c_rescued_entry_from_production_keeps_the_right_side(self):
        """A finished product coming back debits stock and credits the category."""
        self.production_location.valuation_account_id = False
        self.category.reclass_production_account_id = self.account_61211

        move = self._make_in_move(
            self.product, 3.0, unit_cost=10.0, location_id=self.production_location.id)

        self.assertTrue(move.account_move_id)
        self.assertRecordValues(
            move.account_move_id.line_ids.sorted(lambda l: l.debit, reverse=True),
            [
                {"account_id": self.stock_valuation_account.id, "debit": 30.0, "credit": 0.0},
                {"account_id": self.account_61211.id, "debit": 0.0, "credit": 30.0},
            ],
        )

    def test_02d_rescue_keeps_every_other_native_guard(self):
        """Periodic valuation still produces no entry, category or not."""
        self.production_location.valuation_account_id = False
        periodic_product = self.product_avco  # property_valuation = 'periodic'
        periodic_product.categ_id.reclass_production_account_id = self.account_61211

        self._make_in_move(periodic_product, 10.0, unit_cost=10.0)
        move = self._make_out_move(
            periodic_product, 2.0, location_dest_id=self.production_location.id)

        self.assertFalse(
            move.account_move_id,
            "Periodic valuation books at closing: no entry per movement")

    # -------------------------------------------------------------------------
    # PRIORITY 1 / 2 -- CATEGORY AND ANCESTORS
    # -------------------------------------------------------------------------

    def test_03_category_account_replaces_location_account(self):
        """Priority 1: the account of the product category wins."""
        self.category.reclass_production_account_id = self.account_61211

        move = self._consume_into_production()

        counterpart = self._counterpart_lines(move)
        self.assertEqual(counterpart.account_id, self.account_61211)
        self.assertNotIn(
            self.account_location, move.account_move_id.line_ids.mapped("account_id"))
        # Same entry as always: two lines, balanced, same amount.
        self.assertEqual(len(move.account_move_id.line_ids), 2)
        self.assertEqual(sum(move.account_move_id.line_ids.mapped("balance")), 0.0)
        self.assertEqual(counterpart.debit, 20.0)

    def test_04_parent_category_account_is_inherited(self):
        """Priority 2: the account is inherited from the parent category."""
        parent = self.env["product.category"].create({"name": "Reclass Parent"})
        grand_parent = self.env["product.category"].create({"name": "Reclass Grand Parent"})
        parent.parent_id = grand_parent
        self.category.parent_id = parent
        grand_parent.reclass_production_account_id = self.account_60211

        move = self._consume_into_production()

        self.assertEqual(self._counterpart_lines(move).account_id, self.account_60211)

        # The closest ancestor wins over the farthest one.
        parent.reclass_production_account_id = self.account_61211
        move = self._make_out_move(
            self.product, 1.0, location_dest_id=self.production_location.id)
        self.assertEqual(self._counterpart_lines(move).account_id, self.account_61211)

    def test_05_return_from_production_uses_the_same_account(self):
        """Coming back from production credits the very same account."""
        self.category.reclass_production_account_id = self.account_61211
        self._consume_into_production()

        back_move = self._make_in_move(
            self.product, 1.0, unit_cost=10.0, location_id=self.production_location.id)

        counterpart = self._counterpart_lines(back_move)
        self.assertEqual(counterpart.account_id, self.account_61211)
        self.assertEqual(counterpart.credit, 10.0,
                         "The consumption and its return must offset each other")

    # -------------------------------------------------------------------------
    # DIFFERENT PRODUCTS -> DIFFERENT ACCOUNTS IN THE SAME NATIVE ENTRY
    # -------------------------------------------------------------------------

    def test_05b_each_move_resolves_its_own_account(self):
        """Several moves land in one native entry, each with its own account."""
        other_product = self.env["product.product"].create({
            "name": "Other Reclass Product",
            "is_storable": True,
            "standard_price": 10.0,
            "uom_id": self.uom.id,
            "categ_id": self.category_fifo_auto.id,
        })
        self.category.reclass_production_account_id = self.account_61211
        self.category_fifo_auto.reclass_production_account_id = self.account_60211
        self._make_in_move(self.product, 10.0, unit_cost=10.0)
        self._make_in_move(other_product, 10.0, unit_cost=5.0)

        picking = self.env["stock.picking"].create({
            "picking_type_id": self.picking_type_out.id,
            "location_id": self.stock_location.id,
            "location_dest_id": self.production_location.id,
        })
        for product, quantity in ((self.product, 2.0), (other_product, 3.0)):
            self.env["stock.move"].create({
                "picking_id": picking.id,
                "product_id": product.id,
                "product_uom_qty": quantity,
                "product_uom": self.uom.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.production_location.id,
            })
        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
        picking.move_ids.picked = True
        picking._action_done()

        entries = picking.move_ids.mapped("account_move_id")
        self.assertEqual(len(entries), 1, "The native flow groups them in one entry")
        counterparts = entries.line_ids.filtered(
            lambda l: l.account_id != self.stock_valuation_account)
        self.assertEqual(
            counterparts.mapped("account_id"), self.account_61211 | self.account_60211,
            "Each move must resolve the account of its own product category")
        self.assertEqual(sum(entries.line_ids.mapped("balance")), 0.0)

    # -------------------------------------------------------------------------
    # SCOPE
    # -------------------------------------------------------------------------

    def test_06_inventory_locations_keep_their_native_account(self):
        """Scrap and inventory adjustments are out of scope: native account."""
        self.category.reclass_production_account_id = self.account_61211
        account_inventory = self._use_inventory_location_accounting()
        self._make_in_move(self.product, 10.0, unit_cost=10.0)

        move = self._make_out_move(
            self.product, 2.0, location_dest_id=self.inventory_location.id)

        self.assertEqual(self._counterpart_lines(move).account_id, account_inventory)

    def test_06b_inventory_locations_are_never_rescued(self):
        """No account on an inventory location: native silence is preserved.

        Odoo 19 cannot tell a scrap location from an inventory adjustment one, so
        the whole ``inventory`` usage stays native rather than dragging
        adjustments into a reclassification they were never meant for.
        """
        self.category.reclass_production_account_id = self.account_61211
        self.assertFalse(self.inventory_location.valuation_account_id)
        self._make_in_move(self.product, 10.0, unit_cost=10.0)

        move = self._make_out_move(
            self.product, 2.0, location_dest_id=self.inventory_location.id)

        self.assertFalse(
            move.account_move_id,
            "An inventory location without account must keep booking nothing")

    def test_07_plain_delivery_is_not_affected(self):
        """A delivery to a customer keeps its own native account."""
        self.category.reclass_production_account_id = self.account_61211
        account_cogs = self.env["account.account"].create({
            "name": "Cost of goods sold",
            "code": "RECLCOGS",
            "account_type": "expense",
        })
        self.customer_location.valuation_account_id = account_cogs
        self._make_in_move(self.product, 10.0, unit_cost=10.0)

        move = self._make_out_move(self.product, 2.0)

        self.assertEqual(self._counterpart_lines(move).account_id, account_cogs)
        self.assertNotIn(
            self.account_61211,
            move.account_move_id.line_ids.mapped("account_id"),
            "Deliveries have no production location involved")

    def test_08_delivery_without_location_account_is_not_rescued(self):
        """The rescue never widens to customer/supplier locations."""
        self.category.reclass_production_account_id = self.account_61211
        self.assertFalse(self.customer_location.valuation_account_id)
        self._make_in_move(self.product, 10.0, unit_cost=10.0)

        move = self._make_out_move(self.product, 2.0)

        self.assertFalse(
            move.account_move_id,
            "A plain delivery must keep booking nothing, exactly like native")

    def test_08b_receipts_and_deliveries_still_book_nothing(self):
        """Purchase receipts and sale deliveries keep generating no entry at all.

        They are the two flows that natively produce no accounting entry in
        Odoo 19 (no ``valuation_account_id`` on the supplier/customer location),
        and the category account must not turn them into one.
        """
        self.category.reclass_production_account_id = self.account_61211
        self.assertFalse(self.supplier_location.valuation_account_id)
        self.assertFalse(self.customer_location.valuation_account_id)

        receipt = self._make_in_move(self.product, 10.0, unit_cost=10.0)
        self.assertFalse(
            receipt.account_move_id,
            "A purchase receipt must keep booking nothing")
        self.assertFalse(receipt._should_create_account_move())

        delivery = self._make_out_move(self.product, 2.0)
        self.assertFalse(
            delivery.account_move_id,
            "A sale delivery must keep booking nothing")
        self.assertFalse(delivery._should_create_account_move())

        internal = self._make_out_move(
            self.product, 1.0, location_dest_id=self.warehouse.wh_output_stock_loc_id.id)
        self.assertFalse(
            internal.account_move_id,
            "An internal transfer must keep booking nothing")

    # -------------------------------------------------------------------------
    # RESILIENCE
    # -------------------------------------------------------------------------

    def test_09_unknown_native_shape_keeps_native_accounts(self):
        """If the native entry stops looking like we expect, we step aside."""
        self.category.reclass_production_account_id = self.account_61211
        move = self._consume_into_production()
        # Sanity: with the shape we know, the override does apply.
        self.assertEqual(self._counterpart_lines(move).account_id, self.account_61211)

        # A future Odoo splitting the counterpart in two balanced halves: the
        # account of the location is no longer on a single identifiable line.
        unknown_shape = [
            {"account_id": self.stock_valuation_account.id, "debit": 0.0, "credit": 20.0},
            {"account_id": self.account_location.id, "debit": 10.0, "credit": 0.0},
            {"account_id": self.account_location.id, "debit": 10.0, "credit": 0.0},
        ]

        result = move._reclass_apply_account_override(unknown_shape)

        self.assertEqual(
            [vals["account_id"] for vals in result],
            [self.stock_valuation_account.id, self.account_location.id,
             self.account_location.id],
            "An unrecognised shape must be left exactly as the native code built it")

    @mute_logger("odoo.addons.account_reclassification.models.stock_move")
    def test_09b_any_failure_falls_back_to_native_accounts(self):
        """Whatever blows up inside our resolution, the native entry stands."""
        self.category.reclass_production_account_id = self.account_61211

        def _boom(move_self):
            raise ValueError("simulated future incompatibility")

        self.patch(type(self.env["stock.move"]), "_reclass_resolve_counterpart", _boom)
        move = self._consume_into_production()

        self.assertEqual(self._counterpart_lines(move).account_id, self.account_location)
        self.assertEqual(sum(move.account_move_id.line_ids.mapped("balance")), 0.0)

    def test_10_broken_valuation_api_falls_back_to_native(self):
        """Without the native pieces we plug into, nothing of ours runs."""
        self.category.reclass_production_account_id = self.account_61211
        self.patch(
            type(self.env["stock.move"]),
            "_reclass_native_valuation_available",
            lambda move_self: False,
        )

        move = self._consume_into_production()

        self.assertEqual(self._counterpart_lines(move).account_id, self.account_location)
