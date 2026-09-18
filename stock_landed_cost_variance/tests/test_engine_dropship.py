from unittest import SkipTest

from odoo import Command, fields
from odoo.modules.registry import Registry
from odoo.tests import get_db_name, tagged

from .common import RevaluationCommon


@tagged("post_install", "-at_install")
class TestEngineDropship(RevaluationCommon):
    """Dropship: the goods never enter the warehouse, so Odoo values that movement at 0 and a later bill
    has nothing to revalue. Measured before building the engine; this test is here so a future change
    does not start writing values on dropship movements.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if "stock.route" not in Registry(get_db_name()).models:
            raise SkipTest("stock is not installed")
        route = cls.env.ref("stock_dropshipping.route_drop_shipping", raise_if_not_found=False)
        if not route:
            raise SkipTest("stock_dropshipping is not installed")
        cls.product.write({
            "route_ids": [Command.set(route.ids)],
            "seller_ids": [Command.create({"partner_id": cls.partner_b.id, "price": 500.0})]})

    def test_a_late_bill_does_not_revalue_a_dropship(self):
        so = self.env["sale.order"].create({
            "partner_id": self.partner_a.id,
            "order_line": [Command.create({"product_id": self.product.id, "product_uom_qty": 3,
                                           "price_unit": 1000.0, "tax_ids": [Command.clear()]})]})
        so.action_confirm()
        po = so._get_purchase_orders()
        po.button_confirm()
        picking = po.picking_ids
        picking.move_ids.quantity = 3
        picking.move_ids.picked = True
        picking.button_validate()
        invoice = so._create_invoices()
        invoice.invoice_date = fields.Date.today()
        invoice.action_post()

        self.assertTrue(picking.move_ids.is_dropship)
        self.assertAlmostEqual(sum(picking.move_ids.mapped("value")), 0.0, 2,
                               "a dropship is not valued in the warehouse")

        self.bill(po, price=560)
        self.env.invalidate_all()
        self.assertAlmostEqual(sum(picking.move_ids.mapped("value")), 0.0, 2)
        self.assertFalse(self.events(), "nothing to revalue, so no event")
        self.assertAlmostEqual(self.total_value(), 0.0, 2)
        self.assertAlmostEqual(self.balance(self.acc_valuation), 0.0, 2)
