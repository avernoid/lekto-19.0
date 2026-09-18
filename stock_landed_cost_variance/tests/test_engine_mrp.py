from unittest import SkipTest

from odoo import Command
from odoo.tests import tagged

from .common import RevaluationCommon


@tagged("post_install", "-at_install")
class TestEngineManufacturing(RevaluationCommon):
    """Cascade to manufactured goods (design v4, D8). Runs only when mrp_account is installed alongside.

    Component and finished product share the stock valuation account, so accounting is checked on the
    sum of both inventory values.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if "mrp.production" not in cls.env:
            raise SkipTest("mrp_account is not installed")
        cls.component = cls.product
        cls.finished = cls.env["product.product"].create({
            "name": "RV-FINISHED", "is_storable": True, "categ_id": cls.categ.id, "list_price": 1000.0,
            "invoice_policy": "delivery", "taxes_id": [Command.clear()]})
        cls.bom = cls.env["mrp.bom"].create({
            "product_tmpl_id": cls.finished.product_tmpl_id.id, "product_qty": 1,
            "bom_line_ids": [Command.create({"product_id": cls.component.id, "product_qty": 2})]})
        cls.acc_production = cls.env["account.account"].create({
            "name": "Revaluation test production", "code": "RVPROD", "account_type": "asset_current"})
        cls.finished.with_company(cls.company).property_stock_production.valuation_account_id = cls.acc_production

    def manufacture(self, qty):
        production = self.env["mrp.production"].create({
            "product_id": self.finished.id, "product_qty": qty, "bom_id": self.bom.id})
        production.action_confirm()
        production.qty_producing = qty
        production.move_raw_ids.picked = True
        production.button_mark_done()
        return production

    def assertInventoryInStep(self, products):
        self.env.invalidate_all()
        value = sum(p.with_company(self.company).total_value for p in products)
        self.assertAlmostEqual(self.balance(self.acc_valuation), value, 2)
        self.assertAlmostEqual(self.balance(self.acc_production), 0.0, 2, "production account nets to zero")

    def test_component_landed_cost_after_the_finished_product_was_sold(self):
        po = self.purchase(10, 10)
        self.bill(po)
        self.manufacture(2)
        self.invoice(self.sale(1, product=self.finished))
        self.landed_cost(po, 100)
        self.assertInventoryInStep(self.component | self.finished)
        self.assertAlmostEqual(self.total_value(self.finished), 40.0, 2, "one finished unit at (2 x 20)")
        self.assertAlmostEqual(self.balance(self.acc_cogs), 40.0, 2)
        cascade = self.events(self.finished)
        self.assertEqual(cascade.origin, "production")
        self.assertEqual(cascade.parent_id, self.events(self.component))

    def test_finished_product_still_in_stock_follows_the_component(self):
        """Nothing was sold: the cascade must still reach the finished product, or it keeps the old cost
        for ever (Odoo never recomputes it)."""
        po = self.purchase(10, 10)
        self.bill(po)
        self.manufacture(2)
        self.landed_cost(po, 100)
        self.assertInventoryInStep(self.component | self.finished)
        self.assertAlmostEqual(self.total_value(self.component), 120.0, 2, "6 units left at 20")
        self.assertAlmostEqual(self.total_value(self.finished), 80.0, 2, "2 finished at (2 x 20)")
        self.assertAlmostEqual(self.balance(self.acc_cogs), 0.0, 2, "nothing was sold")

    def test_unbuild_after_the_landed_cost(self):
        """An unbuild takes the finished product out and puts the components back, both at the corrected
        cost, so the total inventory value does not move."""
        po = self.purchase(10, 10)
        self.bill(po)
        production = self.manufacture(2)
        self.landed_cost(po, 100)
        total_before = self.total_value(self.component) + self.total_value(self.finished)
        self.env["mrp.unbuild"].create({
            "product_id": self.finished.id, "bom_id": self.bom.id, "product_qty": 1,
            "mo_id": production.id}).action_unbuild()
        self.env.invalidate_all()
        self.assertAlmostEqual(self.total_value(self.finished), 40.0, 2, "one finished unit left, at 2 x 20")
        self.assertAlmostEqual(self.total_value(self.component), 160.0, 2, "6 left plus the 2 given back, at 20")
        self.assertAlmostEqual(self.total_value(self.component) + self.total_value(self.finished), total_before, 2)
        self.assertInventoryInStep(self.component | self.finished)

    def test_by_product_takes_its_cost_share(self):
        byproduct = self.env["product.product"].create({
            "name": "RV-BYPRODUCT", "is_storable": True, "categ_id": self.categ.id})
        self.bom.write({"byproduct_ids": [Command.create({"product_id": byproduct.id, "product_qty": 1,
                                                          "cost_share": 20})]})
        po = self.purchase(10, 10)
        self.bill(po)
        self.manufacture(2)
        self.landed_cost(po, 100)
        self.assertInventoryInStep(self.component | self.finished | byproduct)
        self.assertAlmostEqual(self.total_value(self.finished), 64.0, 2)
        self.assertAlmostEqual(self.total_value(byproduct), 16.0, 2)

    def test_kit_sold_before_the_landed_cost(self):
        kit = self.env["product.product"].create({
            "name": "RV-KIT", "is_storable": True, "list_price": 1000.0, "invoice_policy": "delivery",
            "categ_id": self.categ.id, "taxes_id": [Command.clear()]})
        self.env["mrp.bom"].create({"product_tmpl_id": kit.product_tmpl_id.id, "product_qty": 1, "type": "phantom",
                                    "bom_line_ids": [Command.create({"product_id": self.component.id, "product_qty": 2})]})
        po = self.purchase(10, 10)
        self.bill(po)
        so = self.env["sale.order"].create({
            "partner_id": self.partner_a.id,
            "order_line": [Command.create({"product_id": kit.id, "product_uom_qty": 3, "price_unit": 1000.0,
                                           "tax_ids": [Command.clear()]})]})
        so.action_confirm()
        self._validate(so.picking_ids)
        self.invoice(so)
        self.landed_cost(po, 100)
        self.assertInventoryInStep(self.component)
        self.assertAlmostEqual(self.balance(self.acc_cogs), 120.0, 2, "6 components at 20: kits converted")
