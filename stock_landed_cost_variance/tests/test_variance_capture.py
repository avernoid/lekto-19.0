from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestVarianceCapture(AccountTestInvoicingCommon):
    """The reference scenario, measured on real Odoo 19 before implementing:

        receipt 5 u @ 500 = 2500
        delivery of 3 u   = 1500   (at the standard price of the time)
        landed cost 250 applied afterwards

    Landed unit cost is 550, so inventory is 2 x 550 = 1100 and the cost of
    sales should have been 3 x 550 = 1650.  The core capitalises 250 x 2/5 = 100
    and leaves 150 in the freight expense account, unidentified.  That 150 is
    what this module has to record.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.categ = cls.env["product.category"].create({"name": "AVCO variance"})
        cls.categ.with_company(cls.company).write({
            "property_cost_method": "average",
            "property_valuation": "real_time",
            "property_stock_journal": cls.company_data["default_journal_misc"].id,
        })
        cls.product = cls.env["product.product"].create({
            "name": "VAR-PROD",
            "is_storable": True,
            "categ_id": cls.categ.id,
            "standard_price": 500.0,
        })
        cls.freight = cls.env["product.product"].create({
            "name": "VAR-FREIGHT",
            "type": "service",
            "landed_cost_ok": True,
        })
        cls.wh = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1)
        cls.stock_loc = cls.wh.lot_stock_id
        cls.supplier_loc = cls.env.ref("stock.stock_location_suppliers")
        cls.customer_loc = cls.env.ref("stock.stock_location_customers")

    # ------------------------------------------------------------------
    def _move(self, code, src, dest, qty):
        ptype = self.env["stock.picking.type"].search(
            [("code", "=", code), ("warehouse_id", "=", self.wh.id)], limit=1)
        picking = self.env["stock.picking"].create({
            "picking_type_id": ptype.id,
            "location_id": src.id,
            "location_dest_id": dest.id,
            "move_ids": [Command.create({
                "product_id": self.product.id,
                "product_uom_qty": qty,
                "product_uom": self.product.uom_id.id,
                "location_id": src.id,
                "location_dest_id": dest.id,
            })],
        })
        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            if move.move_line_ids:
                move.move_line_ids[0].quantity = qty
            else:
                move.quantity = qty
            move.picked = True
        picking.button_validate()
        return picking

    def _landed_cost(self, picking, amount):
        cost = self.env["stock.landed.cost"].create({
            "picking_ids": [Command.set(picking.ids)],
            "account_journal_id": self.company_data["default_journal_misc"].id,
            "cost_lines": [Command.create({
                "product_id": self.freight.id,
                "name": "freight",
                "price_unit": amount,
                "split_method": "equal",
                "account_id": self.company_data["default_account_expense"].id,
            })],
        })
        cost.compute_landed_cost()
        cost.button_validate()
        return cost

    # ------------------------------------------------------------------
    def test_split_after_partial_sale(self):
        receipt = self._move("incoming", self.supplier_loc, self.stock_loc, 5.0)
        self._move("outgoing", self.stock_loc, self.customer_loc, 3.0)
        cost = self._landed_cost(receipt, 250.0)

        variance = self.env["stock.value.variance"].search(
            [("move_id", "in", receipt.move_ids.ids)])
        self.assertEqual(len(variance), 1, "one variance per adjustment line")
        self.assertEqual(variance.origin, "landed_cost")
        self.assertAlmostEqual(variance.base_amount, 250.0, 2)
        self.assertAlmostEqual(variance.capitalized_amount, 100.0, 2,
                               "2 of 5 units left in stock")
        self.assertAlmostEqual(variance.expensed_amount, 150.0, 2,
                               "3 of 5 units had already gone")
        self.assertAlmostEqual(variance.valued_qty, 5.0, 2)
        self.assertAlmostEqual(variance.remaining_qty, 2.0, 2)
        self.assertEqual(variance.date.date(), cost.date,
                         "dated on the landed cost, not on the movement")

        # The split must match what the core actually capitalised, or the
        # ledger and the books tell different stories.
        posted = sum(
            line.debit for line in cost.account_move_id.line_ids
            if line.account_id == self.categ.with_company(
                self.company).property_stock_valuation_account_id)
        self.assertAlmostEqual(posted, variance.capitalized_amount, 2)

        # Ledger sign: an incoming move gives the expensed part back.
        self.assertAlmostEqual(variance._ledger_signed_amount(), -150.0, 2)

    def test_split_when_everything_sold(self):
        receipt = self._move("incoming", self.supplier_loc, self.stock_loc, 5.0)
        self._move("outgoing", self.stock_loc, self.customer_loc, 5.0)
        self._landed_cost(receipt, 250.0)

        variance = self.env["stock.value.variance"].search(
            [("move_id", "in", receipt.move_ids.ids)])
        self.assertAlmostEqual(variance.capitalized_amount, 0.0, 2)
        self.assertAlmostEqual(variance.expensed_amount, 250.0, 2,
                               "nothing left: the whole cost belongs to sales")

    def test_no_variance_when_nothing_sold(self):
        receipt = self._move("incoming", self.supplier_loc, self.stock_loc, 5.0)
        self._landed_cost(receipt, 250.0)

        variance = self.env["stock.value.variance"].search(
            [("move_id", "in", receipt.move_ids.ids)])
        self.assertAlmostEqual(variance.capitalized_amount, 250.0, 2)
        self.assertAlmostEqual(variance.expensed_amount, 0.0, 2,
                               "all goods still in stock: nothing to reclassify")
        self.assertAlmostEqual(variance._ledger_signed_amount(), 0.0, 2)

    def test_recompute_blocked_after_validation(self):
        receipt = self._move("incoming", self.supplier_loc, self.stock_loc, 5.0)
        cost = self._landed_cost(receipt, 250.0)
        with self.assertRaises(Exception):
            cost.compute_landed_cost()

    def test_expensed_edit_keeps_the_split_balanced(self):
        receipt = self._move("incoming", self.supplier_loc, self.stock_loc, 5.0)
        self._move("outgoing", self.stock_loc, self.customer_loc, 3.0)
        self._landed_cost(receipt, 250.0)
        variance = self.env["stock.value.variance"].search(
            [("move_id", "in", receipt.move_ids.ids)])

        variance.write({"expensed_amount": 200.0})
        self.assertAlmostEqual(variance.capitalized_amount, 50.0, 2,
                               "the capitalised part follows so base still ties")
        self.assertAlmostEqual(
            variance.base_amount,
            variance.capitalized_amount + variance.expensed_amount, 2)

    def test_ledger_amount_is_signed_by_direction(self):
        receipt = self._move("incoming", self.supplier_loc, self.stock_loc, 5.0)
        self._move("outgoing", self.stock_loc, self.customer_loc, 3.0)
        self._landed_cost(receipt, 250.0)
        variance = self.env["stock.value.variance"].search(
            [("move_id", "in", receipt.move_ids.ids)])
        # Incoming: the ledger gives back the part that belongs to goods gone.
        self.assertAlmostEqual(variance.ledger_amount, -150.0, 2)
        self.assertAlmostEqual(variance._ledger_signed_amount(), -150.0, 2)
        variance.absorbed = True
        self.assertAlmostEqual(variance._ledger_signed_amount(), 0.0, 2,
                               "an absorbed row stops contributing")

    def test_edit_keeps_ledger_amount_in_step(self):
        receipt = self._move("incoming", self.supplier_loc, self.stock_loc, 5.0)
        self._move("outgoing", self.stock_loc, self.customer_loc, 3.0)
        self._landed_cost(receipt, 250.0)
        variance = self.env["stock.value.variance"].search(
            [("move_id", "in", receipt.move_ids.ids)])
        variance.write({"expensed_amount": 200.0})
        self.assertAlmostEqual(variance.ledger_amount, -200.0, 2)
