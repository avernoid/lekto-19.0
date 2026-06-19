# Copyright 2026 Ganemo
# License OPL-1 (Odoo Proprietary License v1.0) - See LICENSE file.
from odoo import Command
from odoo.tests.common import TransactionCase


class AnalyticStockCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")

        cls.valuation_account = cls.env["account.account"].create(
            {
                "name": "Test Stock Valuation",
                "code": "TESTVAL",
                "account_type": "asset_current",
                "reconcile": True,
                "company_ids": [Command.link(cls.company.id)],
            }
        )
        # In Odoo 19 the counterpart of a valuation entry is the valuation
        # account of the non-internal location (customer/supplier/scrap), not a
        # category input/output account.
        cls.counterpart_account = cls.env["account.account"].create(
            {
                "name": "Test Stock Counterpart",
                "code": "TESTCP",
                "account_type": "expense",
                "reconcile": True,
                "company_ids": [Command.link(cls.company.id)],
            }
        )
        cls.stock_journal = cls.env["account.journal"].create(
            {"name": "Test Stock Journal", "code": "TSTJ", "type": "general"}
        )
        cls.company.account_stock_journal_id = cls.stock_journal
        cls.company.account_stock_valuation_id = cls.valuation_account

        cls.category = cls.env["product.category"].create(
            {
                "name": "Real Time Category",
                "property_valuation": "real_time",
                "property_stock_valuation_account_id": cls.valuation_account.id,
                "property_stock_journal": cls.stock_journal.id,
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Analytic Product",
                "type": "consu",
                "is_storable": True,
                "standard_price": 10.0,
                "categ_id": cls.category.id,
            }
        )
        cls.product_b = cls.env["product.product"].create(
            {
                "name": "Analytic Product B",
                "type": "consu",
                "is_storable": True,
                "standard_price": 7.0,
                "categ_id": cls.category.id,
            }
        )

        cls.plan = cls.env["account.analytic.plan"].create({"name": "Test Plan"})
        cls.analytic_account = cls.env["account.analytic.account"].create(
            {"name": "Test Analytic Account", "plan_id": cls.plan.id}
        )
        cls.distribution = {str(cls.analytic_account.id): 100.0}

        cls.warehouse = cls.env.ref("stock.warehouse0")
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.customer_location = cls.env.ref("stock.stock_location_customers")
        cls.supplier_location = cls.env.ref("stock.stock_location_suppliers")
        cls.picking_type_out = cls.env.ref("stock.picking_type_out")
        cls.picking_type_in = cls.env.ref("stock.picking_type_in")

        # Give the external locations a counterpart valuation account so a
        # real-time entry is posted on out/in moves.
        cls.customer_location.valuation_account_id = cls.counterpart_account
        cls.supplier_location.valuation_account_id = cls.counterpart_account

    @classmethod
    def _create_applicability(cls, applicability="optional", picking_type=None):
        return cls.env["account.analytic.applicability"].create(
            {
                "business_domain": "stock_move",
                "applicability": applicability,
                "analytic_plan_id": cls.plan.id,
                "stock_picking_type_id": picking_type.id if picking_type else False,
            }
        )

    def _set_on_hand(self, product, qty):
        self.env["stock.quant"]._update_available_quantity(
            product, self.stock_location, qty
        )

    def _create_picking(
        self, picking_type, src, dest, distribution=False, product=None
    ):
        product = product or self.product
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": src.id,
                "location_dest_id": dest.id,
            }
        )
        self.env["stock.move"].create(
            {
                "picking_id": picking.id,
                "product_id": product.id,
                "product_uom": product.uom_id.id,
                "product_uom_qty": 1.0,
                "location_id": src.id,
                "location_dest_id": dest.id,
                "analytic_distribution": distribution or False,
            }
        )
        return picking

    def _process(self, picking):
        picking.action_confirm()
        picking.action_assign()
        picking.move_ids.quantity = 1.0
        picking.button_validate()

    def _counterpart_lines(self, move):
        return move.account_move_id.line_ids.filtered(
            lambda line: line.account_id != self.valuation_account
        )

    def _valuation_lines(self, move):
        return move.account_move_id.line_ids.filtered(
            lambda line: line.account_id == self.valuation_account
        )
