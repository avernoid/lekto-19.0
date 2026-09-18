from unittest import SkipTest

from odoo import Command
from odoo.tests import tagged

from .common import RevaluationCommon


@tagged("post_install", "-at_install")
class TestEngineSubcontracting(RevaluationCommon):
    """Subcontracting (design v4, D8). Two separate events, both measured before building the engine:

    * a landed cost on a component the subcontractor consumed cascades to the finished product;
    * the subcontractor's bill at a price other than the order's revalues the finished product itself
      (Odoo does that natively on the receipt of the subcontracting order), and the engine handles it
      like any other bill.

    Until the subcontractor is billed, the service is not in the accounts: that gap is native.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if "mrp.production" not in cls.env or "subcontracting_location_id" not in cls.env["res.company"]._fields:
            raise SkipTest("mrp_subcontracting (with accounting) is not installed")
        cls.component = cls.product
        cls.finished = cls.env["product.product"].create({
            "name": "RV-SUBCONTRACTED", "is_storable": True, "categ_id": cls.categ.id, "list_price": 1000.0,
            "invoice_policy": "delivery", "taxes_id": [Command.clear()], "supplier_taxes_id": [Command.clear()]})
        cls.subcontractor = cls.env["res.partner"].create({"name": "RV subcontractor"})
        cls.bom = cls.env["mrp.bom"].create({
            "product_tmpl_id": cls.finished.product_tmpl_id.id, "product_qty": 1, "type": "subcontract",
            "subcontractor_ids": [Command.set(cls.subcontractor.ids)],
            "bom_line_ids": [Command.create({"product_id": cls.component.id, "product_qty": 1})]})
        cls.env["product.supplierinfo"].create({
            "product_tmpl_id": cls.finished.product_tmpl_id.id, "partner_id": cls.subcontractor.id, "price": 30.0})
        cls.acc_production = cls.env["account.account"].create({
            "name": "Revaluation test production (subcontracting)", "code": "RVPRODS",
            "account_type": "asset_current"})
        cls.finished.with_company(cls.company).property_stock_production.valuation_account_id = cls.acc_production

    def resupply(self, qty):
        """Components sent to the subcontractor: an internal movement, not an exit."""
        picking = self.env["stock.picking"].create({
            "picking_type_id": self.wh.int_type_id.id, "location_id": self.wh.lot_stock_id.id,
            "location_dest_id": self.company.subcontracting_location_id.id,
            "move_ids": [Command.create({
                "product_id": self.component.id, "product_uom_qty": qty, "product_uom": self.component.uom_id.id,
                "location_id": self.wh.lot_stock_id.id,
                "location_dest_id": self.company.subcontracting_location_id.id})]})
        return self._validate(picking)

    def subcontract(self, qty, price):
        po = self.env["purchase.order"].create({
            "partner_id": self.subcontractor.id,
            "order_line": [Command.create({"product_id": self.finished.id, "product_qty": qty,
                                           "price_unit": price, "tax_ids": [Command.clear()]})]})
        po.button_confirm()
        receipt = po.picking_ids.filtered(lambda p: p.picking_type_code == "incoming")
        receipt.move_ids.quantity = qty
        receipt.move_ids.picked = True
        receipt.button_validate()
        return po

    def inventory(self):
        self.env.invalidate_all()
        return sum(p.with_company(self.company).total_value for p in (self.component | self.finished))

    def test_landed_cost_on_a_component_the_subcontractor_consumed(self):
        po_component = self.purchase(10, 10)
        self.bill(po_component)
        self.resupply(2)
        self.subcontract(2, 30)
        self.landed_cost(po_component, 100)
        self.env.invalidate_all()
        self.assertAlmostEqual(self.total_value(self.component), 160.0, 2, "8 left at 20")
        self.assertAlmostEqual(self.balance(self.acc_production), 0.0, 2, "production account nets to zero")
        cascade = self.events(self.finished)
        self.assertEqual(cascade.origin, "production")
        self.assertEqual(cascade.parent_id, self.events(self.component))

    def test_subcontractor_bill_at_another_price_after_the_sale(self):
        po_component = self.purchase(10, 10)
        self.bill(po_component)
        self.resupply(2)
        po_finished = self.subcontract(2, 30)
        self.invoice(self.sale(1, product=self.finished))
        self.bill(po_finished, price=35)
        self.env.invalidate_all()
        self.assertAlmostEqual(self.balance(self.acc_valuation), self.inventory(), 2,
                               "once the subcontractor is billed, the account matches the inventory")
