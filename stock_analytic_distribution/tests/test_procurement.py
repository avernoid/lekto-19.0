# Copyright 2026 Ganemo
# License OPL-1 (Odoo Proprietary License v1.0) - See LICENSE file.
from odoo import Command
from odoo.tests import tagged

from .common import AnalyticStockCommon


@tagged("post_install", "-at_install")
class TestProcurement(AnalyticStockCommon):
    def _standalone_move(self, distribution=False):
        return self.env["stock.move"].create(
            {
                "product_id": self.product.id,
                "product_uom": self.product.uom_id.id,
                "product_uom_qty": 1.0,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "analytic_distribution": distribution or False,
            }
        )

    # ------------------------------------------------------------------
    # Propagation hooks
    # ------------------------------------------------------------------
    def test_custom_move_fields(self):
        rule = self.env["stock.rule"].search([], limit=1)
        self.assertIn("analytic_distribution", rule._get_custom_move_fields())

    def test_prepare_procurement_values(self):
        move = self._standalone_move(self.distribution)
        values = move._prepare_procurement_values()
        self.assertEqual(values.get("analytic_distribution"), self.distribution)

    def test_prepare_move_line_vals(self):
        move = self._standalone_move(self.distribution)
        vals = move._prepare_move_line_vals()
        self.assertEqual(vals.get("analytic_distribution"), self.distribution)

    # ------------------------------------------------------------------
    # End-to-end: MTO chain carries the distribution
    # ------------------------------------------------------------------
    def test_mto_chain_propagates_distribution(self):
        intermediate = self.stock_location.copy(
            {"name": "Intermediate", "location_id": self.stock_location.id}
        )
        route = self.env["stock.route"].create(
            {
                "name": "Test MTO",
                "product_selectable": True,
                "rule_ids": [
                    Command.create(
                        {
                            "name": "Intermediate -> Customer (MTO)",
                            "action": "pull",
                            "picking_type_id": self.picking_type_out.id,
                            "location_src_id": intermediate.id,
                            "location_dest_id": self.customer_location.id,
                            "procure_method": "make_to_order",
                        }
                    ),
                    Command.create(
                        {
                            "name": "Stock -> Intermediate",
                            "action": "pull",
                            "picking_type_id": self.picking_type_out.id,
                            "location_src_id": self.stock_location.id,
                            "location_dest_id": intermediate.id,
                            "procure_method": "make_to_stock",
                        }
                    ),
                ],
            }
        )
        self.product.route_ids = [Command.set(route.ids)]

        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_out.id,
                "location_id": intermediate.id,
                "location_dest_id": self.customer_location.id,
            }
        )
        self.env["stock.move"].create(
            {
                "picking_id": picking.id,
                "product_id": self.product.id,
                "product_uom": self.product.uom_id.id,
                "product_uom_qty": 1.0,
                "location_id": intermediate.id,
                "location_dest_id": self.customer_location.id,
                "procure_method": "make_to_order",
                "analytic_distribution": self.distribution,
            }
        )
        picking.action_confirm()
        chained_moves = picking.move_ids.move_orig_ids
        self.assertTrue(chained_moves)
        for move in chained_moves:
            self.assertEqual(move.analytic_distribution, self.distribution)
