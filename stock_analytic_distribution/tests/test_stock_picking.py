# Copyright 2026 Ganemo
# License OPL-1 (Odoo Proprietary License v1.0) - See LICENSE file.
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import AnalyticStockCommon


@tagged("post_install", "-at_install")
class TestStockPicking(AnalyticStockCommon):
    # ------------------------------------------------------------------
    # Accounting: the distribution lands on the journal entry
    # ------------------------------------------------------------------
    def test_outgoing_stamps_counterpart(self):
        self._set_on_hand(self.product, 1)
        picking = self._create_picking(
            self.picking_type_out,
            self.stock_location,
            self.customer_location,
            self.distribution,
        )
        self._process(picking)
        move = picking.move_ids
        self.assertTrue(move.account_move_id)
        for line in self._counterpart_lines(move):
            self.assertEqual(line.analytic_distribution, self.distribution)
        for line in self._valuation_lines(move):
            self.assertFalse(line.analytic_distribution)

    def test_incoming_stamps_counterpart(self):
        picking = self._create_picking(
            self.picking_type_in,
            self.supplier_location,
            self.stock_location,
            self.distribution,
        )
        self._process(picking)
        move = picking.move_ids
        self.assertTrue(move.account_move_id)
        for line in self._counterpart_lines(move):
            self.assertEqual(line.analytic_distribution, self.distribution)
        for line in self._valuation_lines(move):
            self.assertFalse(line.analytic_distribution)

    def test_no_distribution_no_stamp(self):
        self._set_on_hand(self.product, 1)
        picking = self._create_picking(
            self.picking_type_out,
            self.stock_location,
            self.customer_location,
        )
        self._process(picking)
        move = picking.move_ids
        self.assertTrue(move.account_move_id)
        self.assertFalse(
            move.account_move_id.line_ids.filtered("analytic_distribution")
        )

    def test_analytic_items_created_and_linked(self):
        self._set_on_hand(self.product, 1)
        picking = self._create_picking(
            self.picking_type_out,
            self.stock_location,
            self.customer_location,
            self.distribution,
        )
        self._process(picking)
        move = picking.move_ids
        counterpart = self._counterpart_lines(move)
        # Posting the entry generated the analytic items and linked them.
        self.assertTrue(counterpart.analytic_line_ids)
        # And they point to our analytic account.
        self.assertIn(
            self.analytic_account, counterpart.distribution_analytic_account_ids
        )

    # ------------------------------------------------------------------
    # Mandatory plan enforcement
    # ------------------------------------------------------------------
    def test_mandatory_blocks_validation(self):
        self._create_applicability(applicability="mandatory")
        self._set_on_hand(self.product, 1)
        picking = self._create_picking(
            self.picking_type_out,
            self.stock_location,
            self.customer_location,
        )
        with self.assertRaises(ValidationError):
            self._process(picking)

    def test_optional_allows_validation(self):
        self._create_applicability(applicability="optional")
        self._set_on_hand(self.product, 1)
        picking = self._create_picking(
            self.picking_type_out,
            self.stock_location,
            self.customer_location,
        )
        self._process(picking)
        self.assertEqual(picking.state, "done")

    def test_mandatory_scoped_to_operation_type(self):
        # Mandatory only for incoming: an outgoing transfer is not blocked.
        self._create_applicability(
            applicability="mandatory", picking_type=self.picking_type_in
        )
        self._set_on_hand(self.product, 1)
        out_picking = self._create_picking(
            self.picking_type_out,
            self.stock_location,
            self.customer_location,
        )
        self._process(out_picking)
        self.assertEqual(out_picking.state, "done")

        in_picking = self._create_picking(
            self.picking_type_in,
            self.supplier_location,
            self.stock_location,
        )
        with self.assertRaises(ValidationError):
            self._process(in_picking)

    # ------------------------------------------------------------------
    # UX: header default and synchronisation
    # ------------------------------------------------------------------
    def test_picking_header_cascades_to_moves(self):
        picking = self._create_picking(
            self.picking_type_out,
            self.stock_location,
            self.customer_location,
        )
        self.assertFalse(picking.move_ids.analytic_distribution)
        picking.analytic_distribution = self.distribution
        picking._onchange_analytic_distribution()
        self.assertEqual(picking.move_ids.analytic_distribution, self.distribution)

    def test_move_defaults_from_picking_on_create(self):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_out.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "analytic_distribution": self.distribution,
            }
        )
        move = self.env["stock.move"].create(
            {
                "picking_id": picking.id,
                "product_id": self.product.id,
                "product_uom": self.product.uom_id.id,
                "product_uom_qty": 1.0,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            }
        )
        self.assertEqual(move.analytic_distribution, self.distribution)

    def test_move_and_line_stay_in_sync(self):
        self._set_on_hand(self.product, 1)
        picking = self._create_picking(
            self.picking_type_out,
            self.stock_location,
            self.customer_location,
        )
        picking.action_confirm()
        picking.action_assign()
        move = picking.move_ids
        # move -> line
        move.analytic_distribution = self.distribution
        self.assertEqual(
            move.move_line_ids.analytic_distribution, self.distribution
        )
        # line -> move
        move.move_line_ids.analytic_distribution = False
        self.assertFalse(move.analytic_distribution)

    def test_duplicate_does_not_copy_distribution(self):
        picking = self._create_picking(
            self.picking_type_out,
            self.stock_location,
            self.customer_location,
            self.distribution,
        )
        picking.analytic_distribution = self.distribution
        self.assertEqual(picking.analytic_distribution, self.distribution)
        self.assertEqual(picking.move_ids.analytic_distribution, self.distribution)

        new_picking = picking.copy()
        self.assertFalse(new_picking.analytic_distribution)
        self.assertFalse(new_picking.move_ids.analytic_distribution)

    def test_line_override_wins_over_header(self):
        account_2 = self.env["account.analytic.account"].create(
            {"name": "Second Analytic Account", "plan_id": self.plan.id}
        )
        distribution_2 = {str(account_2.id): 100.0}

        self._set_on_hand(self.product, 1)
        self._set_on_hand(self.product_b, 1)
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_out.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            }
        )
        for product in (self.product, self.product_b):
            self.env["stock.move"].create(
                {
                    "picking_id": picking.id,
                    "product_id": product.id,
                    "product_uom": product.uom_id.id,
                    "product_uom_qty": 1.0,
                    "location_id": self.stock_location.id,
                    "location_dest_id": self.customer_location.id,
                }
            )

        # Header autocompletes every move.
        picking.analytic_distribution = self.distribution
        picking._onchange_analytic_distribution()
        move_a = picking.move_ids.filtered(lambda m: m.product_id == self.product)
        move_b = picking.move_ids.filtered(lambda m: m.product_id == self.product_b)
        self.assertEqual(move_a.analytic_distribution, self.distribution)
        self.assertEqual(move_b.analytic_distribution, self.distribution)

        # Override one line: the other keeps the header value.
        move_b.analytic_distribution = distribution_2
        self.assertEqual(move_a.analytic_distribution, self.distribution)
        self.assertEqual(move_b.analytic_distribution, distribution_2)

        # After validation, each move posts with its own distribution. Note all
        # moves validated together share a single journal entry, so we identify
        # each counterpart line by its product.
        self._process(picking)
        amls = picking.move_ids.account_move_id.line_ids.filtered(
            lambda line: line.account_id != self.valuation_account
        )
        line_a = amls.filtered(lambda line: line.product_id == self.product)
        line_b = amls.filtered(lambda line: line.product_id == self.product_b)
        self.assertEqual(line_a.analytic_distribution, self.distribution)
        self.assertEqual(line_b.analytic_distribution, distribution_2)
