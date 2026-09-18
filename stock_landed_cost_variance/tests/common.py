from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class RevaluationHelpers:
    """Fixture and flows shared by every test of the engine, as a mixin.

    It is a mixin and not a base class because some scenarios need another base: the point of sale needs
    ``TestPoSCommon``, and a Peruvian chart needs its own ``setUpClass`` decorator. Whoever mixes it in
    calls ``_setup_revaluation()`` at the end of its own ``setUpClass``.

    Real flows only -- purchase and bill, sale and invoice, freight bill and landed cost, return and
    credit note. No value is written by hand: every expectation below was first measured on these flows
    (valuation_gl_probe, design v4).

    Accounts are explicit so each balance means one thing: stock valuation (category), cost of sales
    (category expense) and freight (freight product expense, also the landed cost line account).
    """

    COST_METHOD = "average"

    @classmethod
    def _setup_revaluation(cls):
        cls.company = cls.company_data["company"]
        # An operational user with real rights (not superuser: ACLs must apply to the engine too).
        groups = cls.env.ref("sales_team.group_sale_manager") | cls.env.ref("purchase.group_purchase_manager")             | cls.env.ref("stock.group_stock_manager") | cls.env.ref("account.group_account_manager")
        if "mrp.production" in cls.env:
            groups |= cls.env.ref("mrp.group_mrp_manager")
        cls.env.user.group_ids |= groups
        cls.acc_cogs = cls.env["account.account"].create({
            "name": "Revaluation test COGS", "code": "RVCOGS", "account_type": "expense_direct_cost"})
        cls.acc_freight = cls.env["account.account"].create({
            "name": "Revaluation test freight", "code": "RVFRT", "account_type": "expense"})
        cls.categ = cls.env["product.category"].create({"name": "Late revaluation"})
        cls.categ.with_company(cls.company).write({
            "property_cost_method": cls.COST_METHOD,
            "property_valuation": "real_time",
            "property_account_expense_categ_id": cls.acc_cogs.id,
        })
        cls.product = cls.env["product.product"].create({
            "name": "RV-PROD", "is_storable": True, "categ_id": cls.categ.id, "list_price": 1000.0,
            "invoice_policy": "delivery", "purchase_method": "receive",
            "taxes_id": [Command.clear()], "supplier_taxes_id": [Command.clear()],
        })
        cls.freight = cls.env["product.product"].create({
            "name": "RV-FREIGHT", "type": "service", "landed_cost_ok": True,
            "property_account_expense_id": cls.acc_freight.id, "supplier_taxes_id": [Command.clear()],
        })
        cls.acc_valuation = cls.product.with_company(cls.company).product_tmpl_id.get_product_accounts()["stock_valuation"]
        cls.wh = cls.env["stock.warehouse"].search([("company_id", "=", cls.company.id)], limit=1)

    def _setup_revaluation_case(self):
        """Every balance is measured from here on, so another module's fixture never leaks into it."""
        last = self.env["account.move.line"].search([], order="id desc", limit=1)
        self.aml_start = last.id or 0

    # ------------------------------------------------------------------ flows
    def _validate(self, picking, qty=None):
        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            wanted = qty if qty is not None else move.product_uom_qty
            if move.move_line_ids:
                move.move_line_ids[0].quantity = wanted
            else:
                move.quantity = wanted
            move.picked = True
        picking.button_validate()
        return picking

    def _redate(self, pickings, day):
        when = datetime.combine(day, datetime.min.time()) + timedelta(hours=10)
        pickings.move_ids.write({"date": when})
        pickings.move_ids.move_line_ids.write({"date": when})

    def purchase(self, qty, price, day=None, product=None):
        po = self.env["purchase.order"].create({
            "partner_id": self.partner_a.id,
            "order_line": [Command.create({"product_id": (product or self.product).id, "product_qty": qty,
                                           "price_unit": price, "tax_ids": [Command.clear()]})]})
        po.button_confirm()
        self._validate(po.picking_ids)
        if day:
            self._redate(po.picking_ids, day)
        return po

    def bill(self, po, price=None, day=None):
        po.action_create_invoice()
        bill = po.invoice_ids.filtered(lambda m: m.state == "draft")
        bill.invoice_date = day or fields.Date.today()
        if price is not None:
            bill.invoice_line_ids.filtered(lambda l: l.product_id == self.product).price_unit = price
        bill.action_post()
        return bill

    def sale(self, qty, day=None, product=None):
        so = self.env["sale.order"].create({
            "partner_id": self.partner_a.id,
            "order_line": [Command.create({"product_id": (product or self.product).id, "product_uom_qty": qty,
                                           "price_unit": 1000.0, "tax_ids": [Command.clear()]})]})
        so.action_confirm()
        self._validate(so.picking_ids, qty)
        if day:
            self._redate(so.picking_ids, day)
        return so

    def invoice(self, so, qty=None, day=None):
        inv = so._create_invoices()
        if qty is not None:
            inv.invoice_line_ids.filtered(lambda l: l.product_id == self.product).quantity = qty
        inv.invoice_date = day or fields.Date.today()
        inv.action_post()
        return inv

    def freight_bill(self, amount, day=None):
        bill = self.env["account.move"].create({
            "move_type": "in_invoice", "partner_id": self.partner_b.id, "invoice_date": day or fields.Date.today(),
            "invoice_line_ids": [Command.create({"product_id": self.freight.id, "quantity": 1,
                                                 "price_unit": amount, "tax_ids": [Command.clear()]})]})
        bill.action_post()
        return bill

    def landed_cost(self, po, amount, day=None):
        if amount > 0:
            self.freight_bill(amount, day)
        vals = {
            "picking_ids": [Command.set(po.picking_ids.ids)],
            "cost_lines": [Command.create({"product_id": self.freight.id, "name": "freight", "price_unit": amount,
                                           "split_method": "equal", "account_id": self.acc_freight.id})],
        }
        if day:
            vals["date"] = day
        cost = self.env["stock.landed.cost"].create(vals)
        cost.compute_landed_cost()
        cost.button_validate()
        return cost

    def return_goods(self, so, qty, day=None):
        picking = so.picking_ids.filtered(lambda p: p.picking_type_code == "outgoing")[:1]
        wizard = self.env["stock.return.picking"].with_context(
            active_id=picking.id, active_ids=picking.ids, active_model="stock.picking").create({"picking_id": picking.id})
        wizard.product_return_moves.quantity = qty
        returned = self._validate(wizard._create_return(), qty)
        if day:
            self._redate(returned, day)
        return returned

    def refund(self, invoice, qty, day=None):
        refund = invoice._reverse_moves([{"invoice_date": day or fields.Date.today()}])
        refund.invoice_line_ids.filtered(lambda l: l.product_id == self.product).quantity = qty
        refund.action_post()
        return refund

    # ------------------------------------------------------------------ measures
    def balance(self, account, day=None):
        domain = [("company_id", "=", self.company.id), ("parent_state", "=", "posted"),
                  ("account_id", "=", account.id), ("id", ">", self.aml_start)]
        if day:
            domain.append(("date", "<=", day))
        return sum(self.env["account.move.line"].search(domain).mapped("balance"))

    def total_value(self, product=None):
        self.env.invalidate_all()
        return (product or self.product).with_company(self.company).total_value

    def assertStockAccountingInStep(self, product=None, msg=""):
        """I1: stock valuation account == Odoo's inventory value."""
        self.assertAlmostEqual(self.balance(self.acc_valuation), self.total_value(product), 2,
                               f"stock valuation account differs from inventory value {msg}")

    def assertKardexInStep(self, product=None):
        """I3 + I4: stored values plus live rows == inventory value; every exit at the engine's cost."""
        product = (product or self.product).with_company(self.company)
        self.env.invalidate_all()
        moves = self.env["stock.move"].search([("product_id", "=", product.id), ("state", "=", "done"),
                                               "|", ("is_in", "=", True), ("is_out", "=", True)])
        live = self.env["stock.value.variance"]._variance_live_rows(moves)
        kardex = sum(m.value if m.is_in else -m.value for m in moves) + sum(live.mapped("ledger_amount"))
        self.assertAlmostEqual(kardex, product.total_value, 2, "Kardex differs from inventory value")
        replay = self.env["stock.move"].with_company(self.company)._variance_replay_costs(product)
        for move_id, cost in replay.items():
            self.assertAlmostEqual(self.env["stock.move"].browse(move_id).value, cost, 2,
                                   "an exit is not at the engine's cost")

    def events(self, product=None):
        return self.env["stock.value.revaluation"].search([("product_id", "=", (product or self.product).id)])

    # ------------------------------------------------------------------ periods
    def set_periods(self):
        today = fields.Date.today()
        self.p3 = (today.replace(day=1), today)
        p2_from = self.p3[0] - relativedelta(months=1)
        self.p2 = (p2_from, self.p3[0] - timedelta(days=1))
        p1_from = p2_from - relativedelta(months=1)
        self.p1 = (p1_from, p2_from - timedelta(days=1))

    def day(self, period, n):
        return period[0] + timedelta(days=n - 1)

    def known_at(self, day, product=None):
        self.env.invalidate_all()
        return (product or self.product).with_company(self.company)._variance_value_known_at(day)[1]


class RevaluationCommon(RevaluationHelpers, AccountTestInvoicingCommon):
    """The usual base: the shared fixture on the generic chart of accounts."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_revaluation()

    def setUp(self):
        super().setUp()
        self._setup_revaluation_case()
