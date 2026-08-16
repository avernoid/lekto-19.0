from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from .test_variance_capture import TestVarianceCapture


@tagged("post_install", "-at_install")
class TestVarianceEntry(TestVarianceCapture):
    """The reclassification entry, and the bill-driven origin."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.acc_valuation = cls.categ.with_company(
            cls.company).property_stock_valuation_account_id
        cls.acc_variation = cls.env["account.account"].create({
            "name": "Variance variation", "code": "VARVAR",
            "account_type": "expense",
        })
        cls.acc_cogs = cls.env["account.account"].create({
            "name": "Variance COGS", "code": "VARCOGS",
            "account_type": "expense_direct_cost",
        })
        cls.categ.with_company(cls.company).write({
            "variance_valuation_account_id": cls.acc_valuation.id,
            "variance_variation_account_id": cls.acc_variation.id,
            "variance_cogs_account_id": cls.acc_cogs.id,
        })

    def _balance(self, account, move):
        return sum(
            line.debit - line.credit
            for line in move.line_ids if line.account_id == account)

    # ------------------------------------------------------------------
    def test_landed_cost_entry_walks_through_inventory(self):
        receipt = self._move("incoming", self.supplier_loc, self.stock_loc, 5.0)
        self._move("outgoing", self.stock_loc, self.customer_loc, 3.0)
        self._landed_cost(receipt, 250.0)
        variance = self.env["stock.value.variance"].search(
            [("move_id", "in", receipt.move_ids.ids)])

        entry = variance.action_post_reclassification()
        self.assertEqual(entry.state, "posted")
        self.assertEqual(variance.variance_move_id, entry)

        # 20/61 then 69/20: the amount passes through inventory before becoming
        # cost of sales, which is the PCGE dynamic asked for.
        self.assertEqual(len(entry.line_ids), 4)
        self.assertAlmostEqual(self._balance(self.acc_valuation, entry), 0.0, 2,
                               "inventory nets to zero: the goods are gone")
        self.assertAlmostEqual(self._balance(self.acc_variation, entry), -150.0, 2)
        self.assertAlmostEqual(self._balance(self.acc_cogs, entry), 150.0, 2)
        self.assertAlmostEqual(
            sum(entry.line_ids.mapped("debit")),
            sum(entry.line_ids.mapped("credit")), 2)

    def test_entry_is_idempotent(self):
        receipt = self._move("incoming", self.supplier_loc, self.stock_loc, 5.0)
        self._move("outgoing", self.stock_loc, self.customer_loc, 3.0)
        self._landed_cost(receipt, 250.0)
        variance = self.env["stock.value.variance"].search(
            [("move_id", "in", receipt.move_ids.ids)])

        variance.action_post_reclassification()
        with self.assertRaises(UserError):
            variance.action_post_reclassification()

    def test_absorbed_variance_is_not_posted(self):
        receipt = self._move("incoming", self.supplier_loc, self.stock_loc, 5.0)
        self._move("outgoing", self.stock_loc, self.customer_loc, 3.0)
        self._landed_cost(receipt, 250.0)
        variance = self.env["stock.value.variance"].search(
            [("move_id", "in", receipt.move_ids.ids)])
        variance.absorbed = True

        with self.assertRaises(UserError):
            variance.action_post_reclassification()

    def test_missing_account_fails_loudly(self):
        self.categ.with_company(self.company).variance_cogs_account_id = False
        receipt = self._move("incoming", self.supplier_loc, self.stock_loc, 5.0)
        self._move("outgoing", self.stock_loc, self.customer_loc, 3.0)
        self._landed_cost(receipt, 250.0)
        variance = self.env["stock.value.variance"].search(
            [("move_id", "in", receipt.move_ids.ids)])

        with self.assertRaises(UserError):
            variance.action_post_reclassification()

    # ------------------------------------------------------------------
    def test_bill_revaluation_is_captured(self):
        """A bill posted above the PO price rewrites a done receipt's value."""
        po = self.env["purchase.order"].create({
            "partner_id": self.partner_a.id,
            "order_line": [Command.create({
                "product_id": self.product.id,
                "product_qty": 5.0,
                "product_uom_id": self.product.uom_id.id,
                "price_unit": 500.0,
            })],
        })
        po.button_confirm()
        picking = po.picking_ids
        picking.move_line_ids.write({"quantity": 5.0, "picked": True})
        picking.button_validate()
        move = po.order_line.move_ids.filtered(lambda m: m.state == "done")
        self.assertAlmostEqual(move.value, 2500.0, 2)

        self._move("outgoing", self.stock_loc, self.customer_loc, 3.0)

        po.action_create_invoice()
        bill = po.invoice_ids
        bill.invoice_date = "2026-01-31"
        bill.invoice_line_ids.write({"price_unit": 560.0})
        bill.action_post()
        move.invalidate_recordset(["value"])
        self.assertAlmostEqual(move.value, 2800.0, 2, "the core rewrote a done move")

        variance = self.env["stock.value.variance"].search(
            [("move_id", "=", move.id), ("origin", "=", "bill")])
        self.assertEqual(len(variance), 1)
        self.assertAlmostEqual(variance.base_amount, 300.0, 2)
        self.assertAlmostEqual(variance.capitalized_amount, 120.0, 2,
                               "2 of 5 units still in stock")
        self.assertAlmostEqual(variance.expensed_amount, 180.0, 2,
                               "(560-500) x 3 units already delivered")
        self.assertEqual(variance.account_move_id, bill)

    def test_bill_entry_leaves_inventory(self):
        """Bill origin under perpetual: the amount is already in inventory, so
        it only has to come out -- no walk through the variation account."""
        po = self.env["purchase.order"].create({
            "partner_id": self.partner_a.id,
            "order_line": [Command.create({
                "product_id": self.product.id,
                "product_qty": 5.0,
                "product_uom_id": self.product.uom_id.id,
                "price_unit": 500.0,
            })],
        })
        po.button_confirm()
        picking = po.picking_ids
        picking.move_line_ids.write({"quantity": 5.0, "picked": True})
        picking.button_validate()
        self._move("outgoing", self.stock_loc, self.customer_loc, 3.0)
        po.action_create_invoice()
        bill = po.invoice_ids
        bill.invoice_date = "2026-01-31"
        bill.invoice_line_ids.write({"price_unit": 560.0})
        bill.action_post()

        variance = self.env["stock.value.variance"].search([("origin", "=", "bill")])
        entry = variance.action_post_reclassification()
        self.assertEqual(len(entry.line_ids), 2)
        self.assertAlmostEqual(self._balance(self.acc_cogs, entry), 180.0, 2)
        self.assertAlmostEqual(self._balance(self.acc_valuation, entry), -180.0, 2)

    # ------------------------------------------------------------------
    def test_bill_after_landed_cost_keeps_both(self):
        """A bill posted after a landed cost must not swallow the landed cost.

        ``_get_value_data`` rebuilds the value from scratch on every
        ``_set_value``: the bill sets the base and ``_get_value_from_extra``
        re-reads the adjustment lines and adds them on top.  So the two
        revaluations are independent and additive -- and the capture must
        measure only the bill's own contribution, or the landed cost would be
        counted twice.
        """
        po = self.env["purchase.order"].create({
            "partner_id": self.partner_a.id,
            "order_line": [Command.create({
                "product_id": self.product.id,
                "product_qty": 5.0,
                "product_uom_id": self.product.uom_id.id,
                "price_unit": 500.0,
            })],
        })
        po.button_confirm()
        picking = po.picking_ids
        picking.move_line_ids.write({"quantity": 5.0, "picked": True})
        picking.button_validate()
        move = po.order_line.move_ids.filtered(lambda m: m.state == "done")
        self.assertAlmostEqual(move.value, 2500.0, 2)

        # 3 of the 5 units leave, then the landed cost, then the bill.
        self._move("outgoing", self.stock_loc, self.customer_loc, 3.0)
        self._landed_cost(picking, 250.0)
        move.invalidate_recordset(["value"])
        self.assertAlmostEqual(move.value, 2750.0, 2, "landed cost added")

        po.action_create_invoice()
        bill = po.invoice_ids
        bill.invoice_date = "2026-01-31"
        bill.invoice_line_ids.write({"price_unit": 560.0})
        bill.action_post()
        move.invalidate_recordset(["value"])

        # 5 x 560 = 2800 from the bill, and the landed cost survives on top.
        self.assertAlmostEqual(move.value, 3050.0, 2,
                               "the landed cost is NOT lost when the bill re-values")

        lc_var = self.env["stock.value.variance"].search(
            [("move_id", "=", move.id), ("origin", "=", "landed_cost")])
        bill_var = self.env["stock.value.variance"].search(
            [("move_id", "=", move.id), ("origin", "=", "bill")])
        self.assertAlmostEqual(lc_var.base_amount, 250.0, 2)
        self.assertAlmostEqual(bill_var.base_amount, 300.0, 2,
                               "only the bill's own contribution, not 550")

        # Landed unit cost is 3050/5 = 610; the 3 units already gone were
        # recognised at 500, so 3 x 110 = 330 belongs to cost of sales.
        total_expensed = lc_var.expensed_amount + bill_var.expensed_amount
        self.assertAlmostEqual(lc_var.expensed_amount, 150.0, 2)
        self.assertAlmostEqual(bill_var.expensed_amount, 180.0, 2)
        self.assertAlmostEqual(total_expensed, 330.0, 2)
        self.assertAlmostEqual(
            total_expensed, 3 * (move.value / 5.0 - 500.0), 2,
            "the two variances together close the gap exactly")
