from odoo.tests import tagged

from .common import RevaluationCommon


@tagged("post_install", "-at_install")
class TestEngineAverage(RevaluationCommon):
    """Scenario matrix of design v4, average cost. Base: buy 5 at 500 (billed), sell 3.

    Expected figures are the economic ones and were measured on the prototype: inventory 2 x 550 = 1 100
    and cost of sales 3 x 550 = 1 650 after a landed cost of 250.
    """

    def _base(self, invoice=True):
        po = self.purchase(5, 500)
        self.bill(po)
        so = self.sale(3)
        inv = self.invoice(so) if invoice else self.env["account.move"]
        return po, so, inv

    def test_a_landed_cost_after_the_sale_was_invoiced(self):
        po, so, inv = self._base()
        self.landed_cost(po, 250)
        self.assertStockAccountingInStep()
        self.assertKardexInStep()
        self.assertAlmostEqual(self.total_value(), 1100.0, 2)
        self.assertAlmostEqual(self.balance(self.acc_cogs), 1650.0, 2, "cost of sales at the landed cost")
        self.assertAlmostEqual(self.balance(self.acc_freight), 0.0, 2, "the whole freight left the freight account")
        exit_move = so.picking_ids.move_ids
        self.assertAlmostEqual(exit_move.value, 1650.0, 2, "the delivery is restated")
        event = self.events()
        self.assertEqual(len(event), 1)
        self.assertEqual(event.state, "posted")
        self.assertEqual(event.origin, "landed_cost")
        self.assertAlmostEqual(event.costed_amount, 150.0, 2)
        self.assertTrue(event.identity_ok)
        row = event.line_ids.filtered(lambda r: r.move_id == exit_move)
        self.assertAlmostEqual(row.ledger_amount, -150.0, 2)
        self.assertTrue(row.absorbed, "the amount is folded into the stored value")

    def test_b_landed_cost_before_invoicing(self):
        po, so, _inv = self._base(invoice=False)
        self.landed_cost(po, 250)
        event = self.events()
        self.assertAlmostEqual(event.pending_amount, 150.0, 2, "not costed yet: stays in inventory")
        self.invoice(so)
        self.assertStockAccountingInStep()
        self.assertAlmostEqual(self.balance(self.acc_cogs), 1650.0, 2)
        self.assertAlmostEqual(self.balance(self.acc_freight), 0.0, 2)

    def test_c_bill_price_after_invoicing(self):
        po = self.purchase(5, 500)
        so = self.sale(3)
        self.invoice(so)
        self.bill(po, price=560)
        self.assertStockAccountingInStep()
        self.assertKardexInStep()
        self.assertAlmostEqual(self.balance(self.acc_cogs), 1680.0, 2)
        self.assertEqual(self.events().origin, "vendor_bill")

    def test_d_bill_price_before_invoicing(self):
        po = self.purchase(5, 500)
        so = self.sale(3)
        self.bill(po, price=560)
        self.invoice(so)
        self.assertStockAccountingInStep()
        self.assertAlmostEqual(self.balance(self.acc_cogs), 1680.0, 2, "no double count")

    def test_e_return_and_credit_note_before_landed_cost(self):
        po, so, inv = self._base()
        self.return_goods(so, 1)
        self.refund(inv, 1)
        self.landed_cost(po, 250)
        self.assertStockAccountingInStep()
        self.assertKardexInStep()
        self.assertAlmostEqual(self.total_value(), 1650.0, 2)
        self.assertAlmostEqual(self.balance(self.acc_cogs), 1100.0, 2, "2 units sold at 550")

    def test_e2_return_before_landed_cost_credit_note_after(self):
        po, so, inv = self._base()
        self.return_goods(so, 1)
        self.landed_cost(po, 250)
        self.refund(inv, 1)
        self.assertStockAccountingInStep()
        self.assertAlmostEqual(self.balance(self.acc_cogs), 1100.0, 2)

    def test_e3_credit_note_after_landed_cost_reverses_our_share(self):
        po, so, inv = self._base()
        self.landed_cost(po, 250)
        self.return_goods(so, 1)
        self.refund(inv, 1)
        self.assertStockAccountingInStep()
        self.assertAlmostEqual(self.total_value(), 1650.0, 2)
        self.assertAlmostEqual(self.balance(self.acc_cogs), 1100.0, 2)
        adjustment = self.env["stock.cost.adjustment"].search([("sale_line_id", "=", so.order_line.id)])
        self.assertAlmostEqual(adjustment.reversed_amount, 50.0, 2)

    def test_f_partial_invoice_next_invoice_does_not_recover_twice(self):
        po = self.purchase(5, 500)
        self.bill(po)
        so = self.sale(3)
        self.invoice(so, qty=2)
        self.landed_cost(po, 250)
        third = self.invoice(so)
        cogs = third.line_ids.filtered(lambda l: l.display_type == "cogs" and l.debit)
        self.assertAlmostEqual(sum(cogs.mapped("debit")), 550.0, 2,
                               "without the extension the 3rd unit would carry 650")
        self.assertStockAccountingInStep()
        self.assertAlmostEqual(self.balance(self.acc_cogs), 1650.0, 2)

    def test_g_two_receipts_landed_cost_on_the_older(self):
        po_a = self.purchase(100, 10)
        self.bill(po_a)
        po_b = self.purchase(100, 10)
        self.bill(po_b)
        self.invoice(self.sale(100))
        self.landed_cost(po_a, 100)
        self.assertStockAccountingInStep()
        self.assertKardexInStep()
        self.assertAlmostEqual(self.total_value(), 1050.0, 2, "average cost spreads the freight on all units")
        self.assertAlmostEqual(self.balance(self.acc_cogs), 1050.0, 2)
        self.assertAlmostEqual(self.balance(self.acc_freight), 0.0, 2)

    def test_h_second_landed_cost(self):
        po, so, inv = self._base()
        self.landed_cost(po, 250)
        self.landed_cost(po, 100)
        self.assertStockAccountingInStep()
        self.assertAlmostEqual(self.balance(self.acc_cogs), 1710.0, 2)
        self.assertEqual(len(self.events()), 2)

    def test_i_negative_landed_cost(self):
        po, so, inv = self._base()
        self.landed_cost(po, 250)
        self.landed_cost(po, -100)
        self.assertStockAccountingInStep()
        self.assertAlmostEqual(self.total_value(), 1060.0, 2)
        self.assertAlmostEqual(self.balance(self.acc_cogs), 1590.0, 2)

    def test_j_invoice_reset_to_draft_and_reposted(self):
        po, so, inv = self._base()
        self.landed_cost(po, 250)
        inv.button_draft()
        inv.action_post()
        self.assertStockAccountingInStep()
        self.assertAlmostEqual(self.balance(self.acc_cogs), 1650.0, 2, "no guard needed: nothing doubles")

    def test_k_bill_then_landed_cost_on_the_same_purchase(self):
        po = self.purchase(5, 500)
        so = self.sale(3)
        self.invoice(so)
        self.bill(po, price=560)
        self.landed_cost(po, 250)
        self.assertStockAccountingInStep()
        self.assertAlmostEqual(self.balance(self.acc_cogs), 1830.0, 2)

    def test_l_negative_stock(self):
        po1 = self.purchase(2, 10)
        self.bill(po1)
        self.invoice(self.sale(5))
        po2 = self.purchase(5, 20)
        self.bill(po2)
        event = self.events().filtered(lambda e: e.origin == "negative_stock")
        self.assertAlmostEqual(event.discard_amount, 30.0, 2, "the value the native replay drops")
        self.invoice(self.sale(1))
        self.assertStockAccountingInStep()
        self.assertKardexInStep()
        self.landed_cost(po1, 50)
        self.assertStockAccountingInStep()
        self.assertKardexInStep()
        self.assertAlmostEqual(self.total_value(), 20.0, 2)
        self.assertTrue(all(self.events().mapped("identity_ok")))

    def test_m_nothing_sold_needs_no_entry_of_ours(self):
        po = self.purchase(5, 500)
        self.bill(po)
        self.landed_cost(po, 250)
        event = self.events()
        self.assertEqual(event.state, "no_entry", "the native landed cost entry already capitalised it all")
        self.assertStockAccountingInStep()

    def test_n_recompute_blocked_after_validation(self):
        po = self.purchase(5, 500)
        cost = self.landed_cost(po, 250)
        with self.assertRaises(Exception):
            cost.compute_landed_cost()

    def test_o_bill_reset_marks_event_outdated_without_blocking(self):
        po = self.purchase(5, 500)
        so = self.sale(3)
        self.invoice(so)
        bill = self.bill(po, price=560)
        event = self.events()
        self.assertEqual(event.state, "posted")
        bill.button_draft()
        event.invalidate_recordset()
        self.assertEqual(event.state, "outdated", "reset is allowed; the event shows it needs review")
