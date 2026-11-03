import logging

from odoo import Command, api, models

_logger = logging.getLogger(__name__)


class StockValueRevaluationDemo(models.Model):
    """Demo data: the three situations that justify this module, as a real distributor lives them.

    Everything is built through the real flows -- purchase, receipt, vendor bill, sale, delivery,
    customer invoice, landed cost -- so the values, the journal entries and the events are genuine and
    can be opened one by one in *Inventory > Reporting > Late Revaluations*.

    The company is an electrical materials distributor in Lima that imports part of its stock: the
    freight and the foreign supplier's invoice arrive weeks after the goods came in, often after they
    were sold. That is the problem this module exists for.
    """

    _inherit = "stock.value.revaluation"

    # ------------------------------------------------------------------ entry point
    @api.model
    def _variance_build_demo(self):
        """Build the three demo scenarios. Idempotent and never fatal.

        Idempotent: it stops as soon as the first demo product exists, so a module update does not
        duplicate anything. Never fatal: a demo that cannot be built (no chart of accounts, no
        warehouse) logs a warning instead of breaking the installation.
        """
        if self.env["product.product"].search_count([("default_code", "=", "CAB-NYY-2X4-100")]):
            return
        try:
            self._variance_demo_late_freight()
            self._variance_demo_bill_at_another_price()
            self._variance_demo_negative_stock()
        except Exception:  # noqa: BLE001 - demo data must never break an install
            _logger.warning("stock_landed_cost_variance: demo data could not be built", exc_info=True)

    # ------------------------------------------------------------------ the three situations
    @api.model
    def _variance_demo_late_freight(self):
        """The freight for the import arrives after the cable was sold.

        5 rolls bought at 500 and billed, 3 sold and invoiced, and only then the forwarding agent
        bills the 250 freight. Odoo capitalises only what is still in stock and leaves 150 in the
        freight account; the module restates the delivery to 1,650 and books those 150 as cost of
        sales, dated on the landed cost.
        """
        product = self._variance_demo_product(
            "CAB-NYY-2X4-100", "Cable NYY 2x4 mm2 0,6/1 kV, rollo de 100 m", 500.0, 1000.0)
        purchase = self._variance_demo_purchase(
            product, 5, 500.0, "Comercial Electrica Villaran S.A.C.", bill=True)
        self._variance_demo_sale(product, 3, invoice=True)
        self._variance_demo_landed_cost(purchase, 250.0)

    @api.model
    def _variance_demo_bill_at_another_price(self):
        """The foreign supplier's invoice comes at a price other than the order's.

        The luminaires are received against the proforma and sold; the commercial invoice arrives
        later for less. The same thing happens when the invoice carries another exchange rate: the
        delivery was valued at a cost that is no longer the real one, and here the difference goes
        the other way -- the stock account ends up BELOW the inventory until the module restates it.
        """
        product = self._variance_demo_product(
            "LUM-VIAL-150", "Luminaria vial LED 150 W IP66", 600.0, 1000.0)
        purchase = self._variance_demo_purchase(
            product, 5, 600.0, "Ningbo Lighting Technology Co., Ltd.", bill=False)
        self._variance_demo_sale(product, 3, invoice=True)
        self._variance_demo_bill(purchase, price=540.0)

    @api.model
    def _variance_demo_negative_stock(self):
        """The counter dispatched before logistics registered the receipt.

        2 hundred bolts at 10 are sold as 5, leaving the stock at -3, and the receipt of the 5
        hundred at 20 that were already on the counter is registered afterwards. Odoo's engine resets
        the average and drops 30 that no movement carries: the module records them on that receipt
        and books them, so the Kardex and the stock account still agree with the inventory.
        """
        product = self._variance_demo_product(
            "FIJ-PH-12X3", "Perno hexagonal 1/2\" x 3\" grado 8.8, ciento", 10.0, 60.0)
        self._variance_demo_purchase(product, 2, 10.0, "Comercial Electrica Villaran S.A.C.", bill=True)
        self._variance_demo_sale(product, 5, invoice=True)
        self._variance_demo_purchase(product, 5, 20.0, "Comercial Electrica Villaran S.A.C.", bill=True)

    # ------------------------------------------------------------------ building blocks
    @api.model
    def _variance_demo_category(self):
        """The product line, valued the way this module needs: average cost, perpetual at invoicing.

        With *Periodic* valuation Odoo posts nothing on invoicing and the whole demo would be silent,
        which is why the category is created here instead of reusing the default one.
        """
        category = self.env["product.category"].search([("name", "=", "Conductores y cables")], limit=1)
        if category:
            return category
        category = self.env["product.category"].create({"name": "Conductores y cables"})
        values = {"property_cost_method": "average", "property_valuation": "real_time"}
        expense = self.env["account.account"].search(
            [("account_type", "=", "expense_direct_cost")], limit=1)
        if expense:
            values["property_account_expense_categ_id"] = expense.id
        category.with_company(self.env.company).write(values)
        return category

    @api.model
    def _variance_demo_product(self, code, name, cost, price):
        """The product, and its Peruvian existence fields when the localisation is there.

        Soft-guarded on the field: this module is generic and installs without the Peruvian
        localisation. When it IS installed, these same movements print in the PLE 13.1 and 3.7, so the
        demo also shows what the two bridges do -- without creating a Peruvian company of its own,
        which would be invasive.
        """
        product = self.env["product.product"].create({
            "name": name,
            "default_code": code,
            "type": "consu",
            "is_storable": True,
            "categ_id": self._variance_demo_category().id,
            "standard_price": cost,
            "list_price": price,
            "purchase_method": "receive",
            "invoice_policy": "delivery",
            "taxes_id": [Command.clear()],
            "supplier_taxes_id": [Command.clear()],
        })
        template = product.product_tmpl_id
        if "l10n_pe_type_of_existence" in template._fields:
            template.l10n_pe_type_of_existence = "1"  # mercaderia
        if "l10n_pe_existence_catalogue" in template._fields:
            template.l10n_pe_existence_catalogue = "9"  # codigo propio de la empresa
        return product

    @api.model
    def _variance_demo_partner(self, name):
        partner = self.env["res.partner"].search([("name", "=", name)], limit=1)
        return partner or self.env["res.partner"].create({"name": name})

    @api.model
    def _variance_demo_purchase(self, product, qty, price, vendor, bill=False):
        purchase = self.env["purchase.order"].create({
            "partner_id": self._variance_demo_partner(vendor).id,
            "order_line": [Command.create({
                "product_id": product.id, "product_qty": qty, "price_unit": price,
                "tax_ids": [Command.clear()]})],
        })
        purchase.button_confirm()
        self._variance_demo_validate(purchase.picking_ids)
        if bill:
            self._variance_demo_bill(purchase)
        return purchase

    @api.model
    def _variance_demo_bill(self, purchase, price=None):
        """Post the vendor bill. With ``price``, at a different one than the order's."""
        purchase.action_create_invoice()
        bill = purchase.invoice_ids.filtered(lambda move: move.state == "draft")
        if not bill:
            return bill
        bill.invoice_date = bill.invoice_date or self.env.cr.now().date()
        if price is not None:
            bill.invoice_line_ids.filtered(lambda line: line.product_id.type == "consu").price_unit = price
        bill.action_post()
        return bill

    @api.model
    def _variance_demo_sale(self, product, qty, invoice=False):
        sale = self.env["sale.order"].create({
            "partner_id": self._variance_demo_partner("Ferreteria El Constructor E.I.R.L.").id,
            "order_line": [Command.create({
                "product_id": product.id, "product_uom_qty": qty, "tax_ids": [Command.clear()]})],
        })
        sale.action_confirm()
        self._variance_demo_validate(sale.picking_ids, qty)
        if invoice:
            moves = sale._create_invoices()
            moves.invoice_date = moves.invoice_date or self.env.cr.now().date()
            moves.action_post()
        return sale

    @api.model
    def _variance_demo_landed_cost(self, purchase, amount):
        """The forwarding agent's bill, and the landed cost that spreads it over the receipt."""
        freight = self.env["product.product"].search([("default_code", "=", "SERV-FLETE-IMP")], limit=1)
        if not freight:
            freight = self.env["product.product"].create({
                "name": "Flete maritimo e internacion",
                "default_code": "SERV-FLETE-IMP",
                "type": "service",
                "landed_cost_ok": True,
                "supplier_taxes_id": [Command.clear()],
            })
        agent = self._variance_demo_partner("Agencia de Carga Callao S.A.C.")
        bill = self.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": agent.id,
            "invoice_date": self.env.cr.now().date(),
            "invoice_line_ids": [Command.create({
                "product_id": freight.id, "quantity": 1, "price_unit": amount,
                "tax_ids": [Command.clear()]})],
        })
        bill.action_post()
        cost = self.env["stock.landed.cost"].create({
            "picking_ids": [Command.set(purchase.picking_ids.ids)],
            "cost_lines": [Command.create({
                "product_id": freight.id, "name": "Flete maritimo e internacion",
                "price_unit": amount, "split_method": "equal"})],
        })
        cost.compute_landed_cost()
        cost.button_validate()
        return cost

    @api.model
    def _variance_demo_validate(self, picking, qty=None):
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
