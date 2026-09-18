from odoo import Command, fields
from odoo.tests import tagged

from .common import RevaluationCommon


@tagged("post_install", "-at_install")
class TestEngineFifo(RevaluationCommon):
    COST_METHOD = "fifo"

    def test_landed_cost_after_invoiced_sale(self):
        po = self.purchase(5, 500)
        self.bill(po)
        self.invoice(self.sale(3))
        self.landed_cost(po, 250)
        self.assertStockAccountingInStep()
        self.assertKardexInStep()
        self.assertAlmostEqual(self.balance(self.acc_cogs), 1650.0, 2)

    def test_two_receipts_landed_cost_on_the_consumed_one(self):
        self.set_periods()
        po_a = self.purchase(100, 10, day=self.day(self.p1, 3))
        self.bill(po_a, day=self.day(self.p1, 3))
        po_b = self.purchase(100, 10, day=self.day(self.p1, 5))
        self.bill(po_b, day=self.day(self.p1, 5))
        so = self.sale(100, day=self.day(self.p1, 10))
        self.invoice(so, day=self.day(self.p1, 10))
        self.landed_cost(po_a, 100, day=self.day(self.p2, 5))
        self.assertStockAccountingInStep()
        self.assertKardexInStep()
        self.assertAlmostEqual(self.total_value(), 1000.0, 2, "FIFO: the older receipt is fully consumed")
        self.assertAlmostEqual(self.balance(self.acc_cogs), 1100.0, 2)


@tagged("post_install", "-at_install")
class TestEngineLots(RevaluationCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product.write({"tracking": "lot", "lot_valuated": True})

    def buy_lot(self, qty, price, day, lot_name):
        po = self.env["purchase.order"].create({
            "partner_id": self.partner_a.id,
            "order_line": [Command.create({"product_id": self.product.id, "product_qty": qty,
                                           "price_unit": price, "tax_ids": [Command.clear()]})]})
        po.button_confirm()
        picking = po.picking_ids
        picking.action_confirm()
        move = picking.move_ids
        move.move_line_ids.unlink()
        self.env["stock.move.line"].create({
            "move_id": move.id, "product_id": self.product.id, "quantity": qty, "lot_name": lot_name,
            "location_id": move.location_id.id, "location_dest_id": move.location_dest_id.id})
        move.picked = True
        picking.button_validate()
        self._redate(picking, day)
        self.bill(po, day=day)
        return po

    def sell_lot(self, qty, day, lot_name):
        so = self.env["sale.order"].create({
            "partner_id": self.partner_a.id,
            "order_line": [Command.create({"product_id": self.product.id, "product_uom_qty": qty,
                                           "price_unit": 1000.0, "tax_ids": [Command.clear()]})]})
        so.action_confirm()
        picking = so.picking_ids
        picking.action_assign()
        move = picking.move_ids
        move.move_line_ids.unlink()
        lot = self.env["stock.lot"].search([("name", "=", lot_name), ("product_id", "=", self.product.id)])
        self.env["stock.move.line"].create({
            "move_id": move.id, "product_id": self.product.id, "quantity": qty, "lot_id": lot.id,
            "location_id": move.location_id.id, "location_dest_id": move.location_dest_id.id})
        move.picked = True
        picking.button_validate()
        self._redate(picking, day)
        self.invoice(so, day=day)
        return so

    def test_average_lot(self):
        self.set_periods()
        po = self.buy_lot(5, 500, self.day(self.p1, 3), "L1")
        self.sell_lot(3, self.day(self.p1, 10), "L1")
        self.landed_cost(po, 250, day=self.day(self.p2, 5))
        self.assertStockAccountingInStep()
        self.assertKardexInStep()
        self.assertAlmostEqual(self.balance(self.acc_cogs), 1650.0, 2)

    def test_fifo_lot_sold_out_afterwards(self):
        self.categ.with_company(self.company).property_cost_method = "fifo"
        self.set_periods()
        po1 = self.buy_lot(5, 500, self.day(self.p1, 3), "L1")
        self.buy_lot(5, 600, self.day(self.p1, 5), "L2")
        self.sell_lot(3, self.day(self.p1, 10), "L1")
        self.landed_cost(po1, 250, day=self.day(self.p2, 5))
        self.assertStockAccountingInStep()
        self.assertAlmostEqual(self.total_value(), 4100.0, 2)
        self.sell_lot(2, self.day(self.p3, 1), "L1")
        self.sell_lot(2, self.day(self.p3, 1), "L2")
        self.assertStockAccountingInStep()
        self.assertKardexInStep()
        self.assertAlmostEqual(self.total_value(), 1800.0, 2)

    def test_fifo_lot_with_two_entries_books_the_native_gap(self):
        """Odoo stores the exit at the lot's stack average (2 571.43) but values the lot by FIFO (3 @ 700):
        171.43 is dropped on that exit and booked, so Kardex, inventory account and value stay together."""
        self.categ.with_company(self.company).property_cost_method = "fifo"
        self.set_periods()
        self.buy_lot(5, 500, self.day(self.p1, 3), "L1")
        self.sell_lot(3, self.day(self.p1, 10), "L1")
        self.buy_lot(5, 700, self.day(self.p1, 12), "L1")
        self.sell_lot(4, self.day(self.p1, 13), "L1")
        self.assertAlmostEqual(self.total_value(), 2100.0, 2)
        self.assertStockAccountingInStep()
        self.assertKardexInStep()
        event = self.events().filtered(lambda e: e.origin == "negative_stock")
        self.assertAlmostEqual(sum(event.mapped("discard_amount")), -171.43, 2)


@tagged("post_install", "-at_install")
class TestEngineConsignment(RevaluationCommon):

    def test_mixed_own_and_consigned_sale(self):
        self.set_periods()
        po = self.purchase(5, 500, day=self.day(self.p1, 3))
        self.bill(po, day=self.day(self.p1, 3))
        supplier = self.env.ref("stock.stock_location_suppliers")
        consigned = self.env["stock.picking"].create({
            "picking_type_id": self.wh.in_type_id.id, "owner_id": self.partner_b.id,
            "location_id": supplier.id, "location_dest_id": self.wh.lot_stock_id.id,
            "move_ids": [Command.create({"product_id": self.product.id, "product_uom_qty": 5,
                                         "product_uom": self.product.uom_id.id, "location_id": supplier.id,
                                         "location_dest_id": self.wh.lot_stock_id.id})]})
        self._validate(consigned)
        self._redate(consigned, self.day(self.p1, 4))
        so = self.env["sale.order"].create({
            "partner_id": self.partner_a.id,
            "order_line": [Command.create({"product_id": self.product.id, "product_uom_qty": 6,
                                           "price_unit": 1000.0, "tax_ids": [Command.clear()]})]})
        so.action_confirm()
        picking = so.picking_ids
        picking.action_assign()
        move = picking.move_ids
        move.move_line_ids.unlink()
        for qty, owner in ((3, False), (3, self.partner_b)):
            self.env["stock.move.line"].create({
                "move_id": move.id, "product_id": self.product.id, "quantity": qty, "owner_id": owner and owner.id,
                "location_id": move.location_id.id, "location_dest_id": move.location_dest_id.id})
        move.picked = True
        picking.button_validate()
        self._redate(picking, self.day(self.p1, 10))
        self.invoice(so, day=self.day(self.p1, 10))
        self.landed_cost(po, 250, day=self.day(self.p2, 5))
        self.assertStockAccountingInStep()
        self.assertKardexInStep()
        self.assertAlmostEqual(self.total_value(), 1100.0, 2, "consigned units are not valued")
        self.assertTrue(self.events().identity_ok)


@tagged("post_install", "-at_install")
class TestEngineForeignCurrency(RevaluationCommon):

    def test_bill_at_another_rate(self):
        self.set_periods()
        eur = self.setup_other_currency("EUR", rates=[
            (fields.Date.to_string(self.p1[0]), 0.25), (fields.Date.to_string(self.p2[0]), 0.20)])
        po = self.env["purchase.order"].create({
            "partner_id": self.partner_a.id, "currency_id": eur.id,
            "order_line": [Command.create({"product_id": self.product.id, "product_qty": 5, "price_unit": 100,
                                           "tax_ids": [Command.clear()]})]})
        po.button_confirm()
        self._validate(po.picking_ids)
        self._redate(po.picking_ids, self.day(self.p1, 3))
        po.picking_ids.move_ids._set_value()
        self.assertAlmostEqual(po.picking_ids.move_ids.value, 2000.0, 2, "5 x 100 EUR at 4")
        self.invoice(self.sale(3, day=self.day(self.p1, 10)), day=self.day(self.p1, 10))
        self.bill(po, day=self.day(self.p2, 5))
        self.assertStockAccountingInStep()
        self.assertKardexInStep()
        self.assertAlmostEqual(self.total_value(), 1000.0, 2, "2 x 100 EUR at 5")
        self.assertAlmostEqual(self.events().costed_amount, 300.0, 2, "exchange difference on the 3 units sold")
