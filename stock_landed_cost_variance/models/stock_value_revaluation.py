import logging

from odoo import Command, _, api, fields, models

_logger = logging.getLogger(__name__)


class StockValueRevaluation(models.Model):
    """A late revaluation event: something revalued goods already gone.

    Design v4 (DISENO_REVALORIZACION_TARDIA_v4.md). When a landed cost, a vendor
    bill (another price or exchange rate, a subcontractor bill), a customer
    credit note or a receipt on negative stock changes the cost of goods that
    already left, Odoo 19 corrects the product cost but never the stored value
    of the exits, and leaves the accounting split without an identifiable
    cause. For each such event and product this model:

    1. folds the exits into the cost Odoo's own engine gives them today (D1, D3);
    2. records every folded amount with the event date (D7);
    3. posts ONE identified journal entry dated on the event (D4);
    4. cascades the change to manufactured goods (D8).

    The identity ``revaluation = delta total_value + G + delta discard`` is
    checked before posting. If it does not hold the event is recorded without
    an entry and flagged, instead of blocking the native operation (D10).
    """

    _name = "stock.value.revaluation"
    _description = "Late Stock Revaluation"
    _order = "date desc, id desc"

    name = fields.Char(string="Reference", required=True, copy=False, readonly=True,
                       default=lambda self: _("New"))
    date = fields.Date(
        string="Event Date", required=True, index=True, readonly=True,
        help="Date of the event: the landed cost date, the accounting date of the "
             "bill or credit note, or the date of the receipt. The journal entry "
             "and every amount of the event carry it.")
    company_id = fields.Many2one("res.company", required=True, index=True, readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id")
    product_id = fields.Many2one("product.product", required=True, index=True, readonly=True)
    origin = fields.Selection(
        [("landed_cost", "Landed Cost"),
         ("vendor_bill", "Vendor Bill"),
         ("customer_refund", "Customer Credit Note"),
         ("negative_stock", "Value Dropped by the Engine"),
         ("production", "Manufacturing Cascade")],
        string="Origin", required=True, readonly=True, index=True)
    landed_cost_id = fields.Many2one("stock.landed.cost", readonly=True, index="btree_not_null")
    source_move_id = fields.Many2one(
        "account.move", string="Source Document", readonly=True, index="btree_not_null",
        help="Vendor bill, vendor credit note or customer credit note behind the event.")
    source_reference = fields.Char(string="Source", readonly=True,
                                   help="Document that triggered the event (e.g. manufacturing order).")
    parent_id = fields.Many2one("stock.value.revaluation", string="Triggered by", readonly=True,
                                index="btree_not_null", ondelete="cascade")
    child_ids = fields.One2many("stock.value.revaluation", "parent_id", string="Cascaded Events")

    revaluation_amount = fields.Monetary(
        string="Revaluation", readonly=True,
        help="Value the event added to (or removed from) the product's history.")
    delta_total_value = fields.Monetary(
        string="Stock Value Change", readonly=True,
        help="Change of the inventory value Odoo computes for the product.")
    costed_amount = fields.Monetary(
        string="Already Costed", readonly=True,
        help="Part belonging to goods whose cost of sales was already posted (invoices, "
             "closed point of sale sessions) or consumed by manufacturing.")
    pending_amount = fields.Monetary(
        string="Not Yet Costed", readonly=True,
        help="Part belonging to goods delivered but not costed yet: it stays in inventory "
             "until their invoice posts the cost of sales at the corrected cost.")
    discard_amount = fields.Monetary(
        string="Value Dropped Change", readonly=True,
        help="Change of the value Odoo's engine drops: goods arriving on negative stock, or a FIFO lot "
             "whose exits took the average of its entries.")
    native_amount = fields.Monetary(
        string="Posted by Odoo", readonly=True,
        help="What the native operation already posted to the stock valuation account.")
    identity_ok = fields.Boolean(
        string="Consistent", readonly=True, default=True,
        help="Unchecked when the revaluation did not match the stock value change plus the "
             "restated exits. No entry is posted in that case; the event is kept for review.")
    note = fields.Text(readonly=True)

    account_move_id = fields.Many2one("account.move", string="Journal Entry", readonly=True,
                                      index="btree_not_null", copy=False)
    line_ids = fields.One2many("stock.value.variance", "revaluation_id", string="Movement Amounts")
    adjustment_ids = fields.One2many("stock.cost.adjustment", "revaluation_id",
                                     string="Cost of Sales Adjustments")
    state = fields.Selection(
        [("posted", "Posted"), ("no_entry", "No Entry Needed"),
         ("outdated", "Outdated"), ("inconsistent", "Inconsistent")],
        compute="_compute_state", string="Status",
        help="Posted: the identified entry is posted. No Entry Needed: Odoo's own "
             "operation already posted everything. Outdated: the entry or its source "
             "document is no longer posted -- review it. Inconsistent: the event did "
             "not add up and no entry was posted.")

    @api.depends("account_move_id.state", "source_move_id.state", "identity_ok")
    def _compute_state(self):
        for event in self:
            if not event.identity_ok:
                event.state = "inconsistent"
            elif event.source_move_id and event.source_move_id.state != "posted":
                event.state = "outdated"
            elif not event.account_move_id:
                event.state = "no_entry"
            elif event.account_move_id.state != "posted":
                event.state = "outdated"
            else:
                event.state = "posted"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("stock.value.revaluation") or _("New")
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------
    @api.model
    def _variance_snapshot(self, product, company):
        product = product.with_company(company)
        return {
            "total_value": product.total_value,
            "discard": self.env["stock.move"].with_company(company)._variance_discard_total(product),
        }

    # ------------------------------------------------------------------
    # The engine
    # ------------------------------------------------------------------
    @api.model
    def _variance_handle_event(self, product, company, before, date, origin, expected,
                               native_amount=0.0, source_splits=None, entry_deltas=None, **refs):
        """Fold, record, account and cascade one event for one product.

        :param before: snapshot taken before the native operation
        :param expected: revaluation the native operation applied (landed cost amount,
            bill delta); used to check the identity
        :param native_amount: what the native operation posted to stock valuation
        :param source_splits: [(account, amount)] counterparts of the revaluation that
            Odoo did NOT capitalise (landed cost lines), summing to expected - native_amount
        :param entry_deltas: {move: delta} incoming moves revalued by a bill (recorded, not folded)
        """
        product = product.with_company(company)
        if not product.is_storable:
            return self.browse()
        Move = self.env["stock.move"].with_company(company)
        currency = company.currency_id

        deltas, return_deltas = Move._variance_fold(product)
        discard_rows = Move._variance_sync_discard_rows(product, date)
        self.env.invalidate_all()
        product = product.with_company(company)
        after = self._variance_snapshot(product, company)
        delta_tv = after["total_value"] - before["total_value"]
        delta_discard = after["discard"] - before["discard"]

        costed_by_key, basis_by_key, pending = {}, {}, 0.0
        for move_id, delta in deltas.items():
            move = Move.browse(move_id)
            returned = sum(Move.search([("origin_returned_move_id", "=", move.id),
                                        ("state", "=", "done")]).mapped("quantity"))
            net_out = move.quantity - returned
            net_delta = delta * (net_out / move.quantity) if move.quantity else 0.0
            key, ratio = move._variance_costed_ratio(net_out)
            costed_by_key[key] = costed_by_key.get(key, 0.0) + net_delta * ratio
            basis_by_key[key] = basis_by_key.get(key, 0.0) + net_out * ratio
            pending += net_delta * (1 - ratio)
        costed = sum(costed_by_key.values())
        revaluation = delta_tv + costed + pending + delta_discard

        nothing = all(currency.is_zero(x) for x in (delta_tv, costed, pending, delta_discard, expected or 0.0))
        if nothing and not deltas and not return_deltas:
            return self.browse()

        identity_ok = expected is None or currency.is_zero(revaluation - expected)
        event = self.sudo().create({
            "date": date, "company_id": company.id, "product_id": product.id, "origin": origin,
            "landed_cost_id": refs.get("landed_cost_id"), "source_move_id": refs.get("source_move_id"),
            "source_reference": refs.get("source_reference"), "parent_id": refs.get("parent_id"),
            "revaluation_amount": revaluation, "delta_total_value": delta_tv, "costed_amount": costed,
            "pending_amount": pending, "discard_amount": delta_discard, "native_amount": native_amount,
            "identity_ok": identity_ok,
            "note": False if identity_ok else _(
                "The native operation revalued %(expected)s but the stock value change plus the "
                "restated exits add up to %(found)s. Typical causes: a movement pinned by a manual "
                "valuation, or a valuation not managed by this module. No entry was posted.",
                expected=expected, found=revaluation),
        })
        self._variance_record_lines(event, deltas, return_deltas, entry_deltas or {}, discard_rows)

        if not identity_ok:
            _logger.warning("stock.value.revaluation %s: identity failed (%s vs %s) for %s",
                            event.name, revaluation, expected, product.display_name)
            return event
        if product.valuation != "real_time":
            return event

        entry, cascades = event._variance_post_entry(
            costed_by_key, basis_by_key, pending, delta_tv, delta_discard,
            native_amount, source_splits or [])
        for production, amount, account in cascades:
            self._variance_cascade_production(production, amount, account, date, event)
        return event

    @api.model
    def _variance_record_lines(self, event, deltas, return_deltas, entry_deltas, discard_rows):
        Variance = self.env["stock.value.variance"].sudo()
        date = fields.Datetime.to_datetime(event.date)
        vals = []
        for move_id, delta in deltas.items():
            move = self.env["stock.move"].browse(move_id)
            vals.append({"move_id": move.id, "company_id": event.company_id.id, "revaluation_id": event.id,
                         "kind": "exit", "date": date, "ledger_amount": -delta, "absorbed": True,
                         "valued_qty": move._get_valued_qty()})
        for move_id, delta in return_deltas.items():
            move = self.env["stock.move"].browse(move_id)
            vals.append({"move_id": move.id, "company_id": event.company_id.id, "revaluation_id": event.id,
                         "kind": "return", "date": date, "ledger_amount": delta, "absorbed": True,
                         "valued_qty": move._get_valued_qty()})
        for move, delta in entry_deltas.items():
            vals.append({"move_id": move.id, "company_id": event.company_id.id, "revaluation_id": event.id,
                         "kind": "entry", "date": date, "ledger_amount": delta, "absorbed": True,
                         "valued_qty": move._get_valued_qty()})
        if vals:
            Variance.create(vals)
        if discard_rows:
            discard_rows.write({"revaluation_id": event.id})

    def _variance_post_entry(self, costed_by_key, basis_by_key, pending, delta_tv, delta_discard,
                             native_amount, source_splits):
        """One identified entry dated on the event (design v4, D4)."""
        self.ensure_one()
        event = self
        company = event.company_id
        currency = company.currency_id
        product = event.product_id.with_company(company)
        accounts = product.product_tmpl_id.get_product_accounts()
        valuation, cogs = accounts["stock_valuation"], accounts["expense"]
        lines, cascades = [], []

        def add(account, amount, label):
            amount = currency.round(amount)
            if currency.is_zero(amount):
                return
            lines.append(Command.create({
                "account_id": account.id, "product_id": product.id, "name": f"{event.name}: {label}",
                "debit": max(amount, 0.0), "credit": max(-amount, 0.0)}))

        add(valuation, delta_tv + pending - native_amount, _("inventory"))
        for (kind, record), amount in costed_by_key.items():
            if kind == "mrp":
                account = record.move_raw_ids.location_dest_id.valuation_account_id[:1] or valuation
                add(account, amount, _("consumed by %s", record.name))
                cascades.append((record, amount, account))
            elif kind in ("sale", "pos"):
                add(cogs, amount, _("cost of sales already posted (%s)", record.display_name))
            else:
                add(cogs, amount, _("cost of sales"))
        add(cogs, delta_discard, _("value dropped by the native engine"))
        for account, amount in source_splits:
            add(account, -amount, _("revaluation source"))

        balance = sum(cmd[2]["debit"] - cmd[2]["credit"] for cmd in lines)
        if lines and not currency.is_zero(balance):
            event.write({"identity_ok": False, "note": _(
                "The entry would not balance (%s). No entry was posted.", balance)})
            return self.env["account.move"], []
        if not lines:
            return self.env["account.move"], cascades

        journal = company.account_stock_journal_id or self.env["account.journal"].search(
            [("type", "=", "general"), ("company_id", "=", company.id)], limit=1)
        move = self.env["account.move"].sudo().with_context(variance_skip_engine=True).create({
            "move_type": "entry", "date": event.date, "ref": _("Late revaluation %s", event.name),
            "journal_id": journal.id, "company_id": company.id, "line_ids": lines})
        move._post()
        event.account_move_id = move
        Adjustment = self.env["stock.cost.adjustment"].sudo()
        for (kind, record), amount in costed_by_key.items():
            if kind == "sale" and not currency.is_zero(amount):
                Adjustment.create({"revaluation_id": event.id, "sale_line_id": record.id,
                                   "amount": currency.round(amount), "basis_qty": basis_by_key[(kind, record)]})
        return move, cascades

    @api.model
    def _variance_cascade_production(self, production, amount, account, date, parent):
        """Component cost changed: revalue finished goods and by-products natively, by cost share."""
        Move = self.env["stock.move"]
        finished = production.move_finished_ids.filtered(
            lambda m: m.state == "done" and m.product_id == production.product_id)
        byproducts = production.move_byproduct_ids.filtered(lambda m: m.state == "done") \
            if "move_byproduct_ids" in production._fields else Move
        byproduct_share = sum(byproducts.mapped("cost_share"))
        targets = [(production.product_id, finished, 1 - byproduct_share / 100.0)]
        for product in byproducts.product_id:
            moves = byproducts.filtered(lambda m, p=product: m.product_id == p)
            targets.append((product, moves, sum(moves.mapped("cost_share")) / 100.0))
        events = self.browse()
        company = production.company_id
        for product, moves, ratio in targets:
            share = amount * ratio
            if not moves or company.currency_id.is_zero(share):
                continue
            before = self._variance_snapshot(product, company)
            qty = sum(moves.mapped("quantity"))
            before_values = {m.id: m.value for m in moves}
            for move in moves:
                move.price_unit = move.price_unit + share / qty
            moves._set_value()
            self.env.flush_all()
            entry_deltas = {m: m.value - before_values[m.id] for m in moves
                            if not company.currency_id.is_zero(m.value - before_values[m.id])}
            events |= self._variance_handle_event(
                product, company, before, date, "production", share,
                native_amount=0.0, source_splits=[(account, share)], entry_deltas=entry_deltas,
                source_reference=production.name, parent_id=parent.id)
        return events

    @api.model
    def _variance_handle_negative_stock(self, product, company, before):
        """An entry landed on stock <= 0: book the value the native replay drops (design v4, D9).

        A receipt is not a revaluation -- its own value is new stock -- so only the discard change is
        accounted: Dr cost of sales / Cr inventory. Exits restated by a backdated receipt are folded and
        recorded, but not accounted: the event is flagged for review instead of guessing their counterpart.
        """
        product = product.with_company(company)
        Move = self.env["stock.move"].with_company(company)
        currency = company.currency_id
        date = fields.Date.context_today(self)
        deltas, return_deltas = Move._variance_fold(product)
        discard_rows = Move._variance_sync_discard_rows(product, date)
        after = self._variance_snapshot(product, company)
        delta_discard = after["discard"] - before["discard"]
        if currency.is_zero(delta_discard) and not deltas and not return_deltas:
            return self.browse()
        backdated = bool(deltas or return_deltas)
        event = self.sudo().create({
            "date": date, "company_id": company.id, "product_id": product.id, "origin": "negative_stock",
            "discard_amount": delta_discard, "revaluation_amount": delta_discard, "identity_ok": not backdated,
            "note": _("The receipt changed the cost of exits done before it (backdated receipt). They were "
                      "restated, but no entry was posted for them.") if backdated else False,
        })
        self._variance_record_lines(event, deltas, return_deltas, {}, discard_rows)
        if backdated or product.valuation != "real_time" or currency.is_zero(delta_discard):
            return event
        accounts = product.product_tmpl_id.get_product_accounts()
        journal = company.account_stock_journal_id or self.env["account.journal"].search(
            [("type", "=", "general"), ("company_id", "=", company.id)], limit=1)
        amount = currency.round(delta_discard)
        label = _("%s: value dropped by the native engine", event.name)
        move = self.env["account.move"].sudo().with_context(variance_skip_engine=True).create({
            "move_type": "entry", "date": date, "ref": _("Late revaluation %s", event.name),
            "journal_id": journal.id, "company_id": company.id, "line_ids": [
                Command.create({"account_id": accounts["expense"].id, "product_id": product.id, "name": label,
                                "debit": max(amount, 0.0), "credit": max(-amount, 0.0)}),
                Command.create({"account_id": accounts["stock_valuation"].id, "product_id": product.id,
                                "name": label, "debit": max(-amount, 0.0), "credit": max(amount, 0.0)})]})
        move._post()
        event.account_move_id = move
        return event

    # ------------------------------------------------------------------
    # Credit notes (design v4, D6)
    # ------------------------------------------------------------------
    @api.model
    def _variance_reverse_for_refund(self, refund):
        """Average cost: a credit note reverses cost of sales at the original invoice price, so the
        share of our adjustment that belongs to the returned units is reversed with it."""
        Adjustment = self.env["stock.cost.adjustment"].sudo()
        Move = self.env["stock.move"]
        company = refund.company_id
        currency = company.currency_id
        for line in refund.invoice_line_ids.sale_line_ids:
            product = line.product_id.with_company(company)
            if product.lot_valuated or product.cost_method != "average" or product.valuation != "real_time":
                continue
            adjustments = Adjustment.search([("sale_line_id", "=", line.id), ("basis_qty", ">", 0),
                                             ("revaluation_id.account_move_id.state", "=", "posted")])
            if not adjustments:
                continue
            invoiced_net = line._variance_costed_qty()
            moves = line.move_ids.filtered(lambda m: m.state == "done" and m.is_out)
            returned = sum(Move.search([("origin_returned_move_id", "in", moves.ids),
                                        ("state", "=", "done")]).mapped("quantity"))
            net_out = sum(moves.mapped("quantity")) - returned
            accounts = product.product_tmpl_id.get_product_accounts()
            for adjustment in adjustments:
                per_unit = (adjustment.amount - adjustment.reversed_amount) / adjustment.basis_qty
                new_basis = max(0.0, min(adjustment.basis_qty, net_out, invoiced_net))
                undo = currency.round(per_unit * (adjustment.basis_qty - new_basis))
                if currency.is_zero(undo):
                    continue
                event = adjustment.revaluation_id
                journal = company.account_stock_journal_id or event.account_move_id.journal_id
                label = _("%(refund)s: late revaluation %(event)s back to stock",
                          refund=refund.name, event=event.name)
                move = self.env["account.move"].sudo().with_context(variance_skip_engine=True).create({
                    "move_type": "entry", "date": refund.date, "ref": label, "journal_id": journal.id,
                    "company_id": company.id, "line_ids": [
                        Command.create({"account_id": accounts["stock_valuation"].id, "product_id": product.id,
                                        "name": label, "debit": max(undo, 0.0), "credit": max(-undo, 0.0)}),
                        Command.create({"account_id": accounts["expense"].id, "product_id": product.id,
                                        "name": label, "debit": max(-undo, 0.0), "credit": max(undo, 0.0)})]})
                move._post()
                self.sudo().create({
                    "date": refund.date, "company_id": company.id, "product_id": product.id,
                    "origin": "customer_refund", "source_move_id": refund.id, "parent_id": event.id,
                    "revaluation_amount": 0.0, "costed_amount": -undo, "delta_total_value": undo,
                    "account_move_id": move.id,
                })
                adjustment.write({"basis_qty": new_basis, "reversed_amount": adjustment.reversed_amount + undo})

    # ------------------------------------------------------------------
    def action_view_entry(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "res_model": "account.move",
                "res_id": self.account_move_id.id, "view_mode": "form"}
