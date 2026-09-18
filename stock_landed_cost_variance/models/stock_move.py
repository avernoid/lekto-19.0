import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    variance_line_ids = fields.One2many(
        "stock.value.variance", "move_id", string="Value Variances",
        help="Amounts late revaluations recorded on this movement: exits restated to "
             "the corrected cost, returns re-derived, bill revaluations and negative "
             "stock discards, each with the date of its event.")
    variance_count = fields.Integer(
        string="Value Variance Count", compute="_compute_variance_count",
        help="How many late revaluation amounts were recorded on this movement.")

    @api.depends("variance_line_ids")
    def _compute_variance_count(self):
        for move in self:
            move.variance_count = len(move.variance_line_ids)

    def action_view_value_variances(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Value Variances"),
            "res_model": "stock.value.variance",
            "view_mode": "list,form",
            "domain": [("move_id", "=", self.id)],
        }

    # ------------------------------------------------------------------
    # Negative stock: an entry landing on stock <= 0 (design v4, D9)
    # ------------------------------------------------------------------
    def _action_done(self, cancel_backorder=False):
        Revaluation = self.env["stock.value.revaluation"]
        pending = {}
        if not self.env.context.get("variance_skip_engine"):
            for move in self.filtered(lambda m: m.product_id.is_storable and (
                    m._is_in() or m._is_out() and m.product_id.lot_valuated)):
                key = (move.product_id, move.company_id)
                if key in pending:
                    continue
                product = move.product_id.with_company(move.company_id)
                if product.cost_method == "standard":
                    continue
                # Receipt on stock <= 0 (average reset), or any move of a FIFO lot-valuated product, whose
                # exits take the lot's stack average while its value is true FIFO (see _variance_replay_lots).
                if product.lot_valuated and product.cost_method == "fifo" \
                        or product._with_valuation_context().qty_available <= 0:
                    pending[key] = Revaluation._variance_snapshot(product, move.company_id)
        moves = super()._action_done(cancel_backorder=cancel_backorder)
        for (product, company), before in pending.items():
            Revaluation._variance_handle_negative_stock(product, company, before)
        return moves

    # ------------------------------------------------------------------
    # The cost Odoo's own engine gives each exit today (design v4, D3)
    # ------------------------------------------------------------------
    @api.model
    def _variance_has_consignment(self, product):
        return bool(self.env["stock.move.line"].sudo().search_count([
            ("product_id", "=", product.id), ("state", "=", "done"), ("owner_id", "!=", False)], limit=1))

    @api.model
    def _variance_avco_report(self, product):
        report = self.env["stock.avco.report"].sudo().search([
            ("product_id", "=", product.id), ("company_id", "=", self.env.company.id)])
        report.mapped("total_value")
        return report.sorted(lambda r: (r.date, r.id))

    @api.model
    def _variance_replay_costs(self, product):
        """{exit move id: cost Odoo's engine gives it with today's incoming values}.

        * average, no consignment, no lots: ``stock.avco.report`` -- the core's own replay, ordered by
          (date, id);
        * everything else: a line-by-line mirror of the native method (``_run_average_batch``,
          ``_run_fifo`` / ``_run_fifo_get_stack``, lot variants) walked in (date, id) order.

        Why mirrors and not the native methods with ``at_date``: those filter ``date <= at_date``, so
        moves sharing a timestamp (a receipt and a delivery validated in the same second) fall on the
        wrong side of "just before" -- measured, a FIFO delivery came out at twice its cost. The report
        also counts consigned units while the engine does not (measured). The mirrors are checked
        against the native methods in ``test_engine_parity``.
        """
        return self._variance_replay(product)[0]

    @api.model
    def _variance_replay(self, product):
        """(costs {exit id: cost}, dropped {entry id: value dropped when it arrived on stock <= 0})."""
        product = product.with_company(self.env.company)
        if product.cost_method not in ("average", "fifo"):
            return {}, {}
        if not product.lot_valuated and product.cost_method == "average" \
                and not self._variance_has_consignment(product):
            report = self._variance_avco_report(product)
            costs, dropped, previous = {}, {}, 0.0
            for rec in report:
                if rec.res_model_name == "stock.move":
                    if rec.quantity > 0:
                        amount = previous + rec.value - rec.total_value
                        if not self.env.company.currency_id.is_zero(amount):
                            dropped[rec.id] = amount
                    elif self.browse(rec.id).is_out:
                        costs[rec.id] = abs(rec.added_value)
                previous = rec.total_value
            return costs, dropped
        moves = self.search([("product_id", "=", product.id), ("company_id", "=", self.env.company.id),
                             ("state", "=", "done"), "|", ("is_in", "=", True), ("is_out", "=", True)],
                            order="date, id")
        if product.lot_valuated:
            return self._variance_replay_lots(product, moves)
        if product.cost_method == "average":
            return self._variance_replay_average(product, moves)
        return self._variance_replay_fifo(product, moves)

    @api.model
    def _variance_replay_average(self, product, moves):
        """Mirror of ``_run_average_batch`` (stock_account/models/product.py:469-515), no anchors."""
        costs, dropped = {}, {}
        currency = self.env.company.currency_id
        quantity = value = 0.0
        average = moves[:1].value / moves[:1]._get_valued_qty() if moves and moves[:1]._get_valued_qty() else 0.0
        for move in moves:
            if move.is_in:
                in_qty, in_value = move._get_valued_qty(), move.value
                previous_qty = quantity
                quantity += in_qty
                if previous_qty > 0:
                    value += in_value
                    average = value / quantity
                else:
                    before = value + in_value
                    average = in_value / in_qty if in_qty else average
                    value = average * quantity
                    if not currency.is_zero(before - value):
                        dropped[move.id] = before - value
            if move.is_out:
                out_qty = move._get_valued_qty()
                costs[move.id] = out_qty * average
                value -= out_qty * average
                quantity -= out_qty
        return costs, dropped

    @api.model
    def _variance_replay_fifo(self, product, moves):
        """Mirror of ``_run_fifo`` + ``_run_fifo_get_stack`` (product.py:533-624) evaluated just before
        each exit in (date, id) order; entry values are today's."""
        costs, dropped = {}, {}
        currency = self.env.company.currency_id
        ins, available, ledger, accounted = [], 0.0, 0.0, 0.0
        for move in moves:
            if move.is_in:
                ins.append(move)
                available += move._get_valued_qty()
                ledger += move.value
                engine = self._variance_fifo_stack_value(product, ins, available)
                if not currency.is_zero(ledger - engine - accounted):
                    dropped[move.id] = ledger - engine - accounted
                    accounted += dropped[move.id]
            if move.is_out:
                qty = move._get_valued_qty()
                costs[move.id] = self._variance_fifo_cost(product, ins, available, qty)
                ledger -= costs[move.id]
                available -= qty
        return costs, dropped

    @api.model
    def _variance_fifo_stack(self, ins, available):
        """Newest entries covering ``available``, oldest first, and the quantity taken from the oldest."""
        stack, size, first_qty = [], available, 0.0
        for move in reversed(ins):
            if size <= 0:
                break
            in_qty = move._get_valued_qty()
            stack.append(move)
            first_qty = min(in_qty, size)
            size -= in_qty
        stack.reverse()
        return stack, first_qty

    @api.model
    def _variance_fifo_cost(self, product, ins, available, quantity):
        stack, qty_on_first = self._variance_fifo_stack(ins, available) if available > 0 else ([], 0.0)
        cost, last = 0.0, False
        while quantity > 0 and stack:
            move = stack.pop(0)
            last = move
            if qty_on_first:
                in_qty = qty_on_first
                in_value = move.value * in_qty / move._get_valued_qty()
                qty_on_first = 0.0
            else:
                in_qty, in_value = move._get_valued_qty(), move.value
            if in_qty > quantity:
                in_value = in_value * quantity / in_qty
                in_qty = quantity
            cost += in_value
            quantity -= in_qty
        if quantity > 0:
            cost += quantity * (last.value / last.quantity if last and last.quantity else product.standard_price)
        return cost

    @api.model
    def _variance_fifo_stack_value(self, product, ins, available):
        if available <= 0:
            return available * product.standard_price
        return self._variance_fifo_cost(product, ins, available, available)

    @api.model
    def _variance_replay_lots(self, product, moves):
        """Lot-valuated: an exit line is worth ``lot.standard_price`` (stock_move.py:329-337), and Odoo
        refreshes that price only when an entry of the lot is valued (``stock.lot._update_standard_price``).
        So, per lot in (date, id) order, the price is recomputed at each entry and read at each exit:
        average mirrors ``_run_avco(lot)``; FIFO mirrors ``_run_fifo_batch(lot)`` -- the newest entries
        covering the lot quantity at that moment, divided by that quantity.

        The lot's inventory value, though, is ``_run_fifo(qty, lot)`` (stock_lot.py:46-49): true FIFO.
        When a lot has entries at different prices, the exit takes the stack *average* while the stock
        left is valued at the *newest* entries -- measured: L1 5 @ 500, sell 3, 5 @ 700, sell 4 stores
        2 571.43 while FIFO gives 2 400, and the lot is worth 171.43 more than its movements add up to.
        That gap is returned as dropped on the move where it appears, exactly like the average reset on
        negative stock: no movement value can carry it.

        Known limit: when a revaluation re-values entries of a lot after part of it was sold, Odoo
        refreshes the price with the quantity left *at that moment*; the replay keeps the price of the
        last entry. Single-entry lots (the usual case) are identical."""
        costs, dropped = {}, {}
        currency = self.env.company.currency_id
        by_lot = {}
        for move in moves:
            for line in move.move_line_ids:
                if line.lot_id:
                    by_lot.setdefault(line.lot_id, [])
                    if move not in by_lot[line.lot_id]:
                        by_lot[line.lot_id].append(move)
        prices_at = {}
        for lot, lot_moves in by_lot.items():
            quantity = value = average = 0.0
            ins, available, fifo_price = [], 0.0, product.standard_price
            ledger = gap = 0.0
            for move in lot_moves:
                lot_qty = move._get_valued_qty(lot)
                if move.is_in:
                    valued = move._get_valued_qty()
                    lot_value = move.value * lot_qty / valued if valued else 0.0
                    ledger += lot_value
                    if product.cost_method == "average":
                        previous = quantity
                        quantity += lot_qty
                        if previous > 0:
                            value += lot_value
                            average = value / quantity
                        else:
                            average = lot_value / lot_qty if lot_qty else average
                            value = average * quantity
                    else:
                        ins.append((lot_qty, lot_value))
                        available += lot_qty
                        fifo_price = self._variance_lot_stack_price(ins, available, fifo_price)
                if move.is_out:
                    if product.cost_method == "average":
                        price = average
                        value -= lot_qty * average
                        quantity -= lot_qty
                    else:
                        price = fifo_price
                        available -= lot_qty
                    prices_at[(move.id, lot.id)] = price
                    ledger -= price * lot_qty
                if product.cost_method == "average":
                    engine = value
                elif available > 0:
                    engine = self._variance_lot_fifo_value(ins, available)
                else:
                    engine = available * fifo_price
                change = (ledger - engine) - gap
                if not currency.is_zero(change):
                    dropped[move.id] = dropped.get(move.id, 0.0) + change
                    gap += change
        for move in moves.filtered("is_out"):
            costs[move.id] = sum(
                prices_at.get((move.id, line.lot_id.id), product.standard_price) * line.quantity_product_uom
                for line in move.move_line_ids)
        return costs, dropped

    @api.model
    def _variance_lot_fifo_value(self, ins, available):
        """Value of the newest lot entries covering ``available`` -- the lot's native FIFO value."""
        remaining, value = available, 0.0
        for lot_qty, lot_value in reversed(ins):
            if remaining <= 0:
                break
            use = min(lot_qty, remaining)
            value += lot_value * use / lot_qty if lot_qty else 0.0
            remaining -= use
        return value

    @api.model
    def _variance_lot_stack_price(self, ins, available, previous):
        """Native lot FIFO price: value of the newest lot entries covering the lot quantity / quantity."""
        taken = min(available, sum(qty for qty, _value in ins))
        return self._variance_lot_fifo_value(ins, available) / taken if taken > 0 else previous

    # ------------------------------------------------------------------
    # Fold (design v4, D1)
    # ------------------------------------------------------------------
    @api.model
    def _variance_fold(self, product, max_rounds=6):
        """Write exits at the engine's cost; re-derive customer returns natively; repeat until stable.

        Returns ({exit id: delta}, {return id: delta}).
        """
        product = product.with_company(self.env.company)
        currency = self.env.company.currency_id
        deltas, return_deltas = {}, {}
        for _round in range(max_rounds):
            self.env.flush_all()
            self.env.invalidate_all()
            changed = False
            for move_id, target in self._variance_replay_costs(product).items():
                move = self.browse(move_id)
                delta = currency.round(target) - move.value
                if currency.is_zero(delta):
                    continue
                deltas[move_id] = deltas.get(move_id, 0.0) + delta
                move.value = currency.round(target)
                changed = True
            returns = self.search([
                ("product_id", "=", product.id), ("company_id", "=", self.env.company.id),
                ("state", "=", "done"), ("is_in", "=", True), ("origin_returned_move_id.is_out", "=", True)])
            before = {m.id: m.value for m in returns}
            if returns:
                returns._set_value()
                self.env.flush_all()
            for move in returns:
                delta = move.value - before[move.id]
                if not currency.is_zero(delta):
                    return_deltas[move.id] = return_deltas.get(move.id, 0.0) + delta
                    changed = True
            if not changed:
                break
        return deltas, return_deltas

    # ------------------------------------------------------------------
    # Negative stock discard (design v4, D9)
    # ------------------------------------------------------------------
    @api.model
    def _variance_discard_by_entry(self, product):
        """{entry move id: value the engine drops when that entry arrives on stock <= 0}."""
        return self._variance_replay(product)[1]

    @api.model
    def _variance_discard_total(self, product):
        return sum(self._variance_discard_by_entry(product).values())

    @api.model
    def _variance_sync_discard_rows(self, product, date):
        """Live rows so every ledger carries what the engine drops: one dated delta row per change."""
        Variance = self.env["stock.value.variance"].sudo()
        currency = self.env.company.currency_id
        dropped = self._variance_discard_by_entry(product)
        existing = Variance.search([("product_id", "=", product.id), ("company_id", "=", self.env.company.id),
                                    ("kind", "=", "negative_stock")])
        by_move = {}
        for row in existing:
            by_move[row.move_id.id] = by_move.get(row.move_id.id, 0.0) - row.ledger_amount
        created = Variance
        for move_id in set(dropped) | set(by_move):
            change = dropped.get(move_id, 0.0) - by_move.get(move_id, 0.0)
            if currency.is_zero(change):
                continue
            move = self.browse(move_id)
            created |= Variance.create({
                "move_id": move.id, "company_id": self.env.company.id, "kind": "negative_stock",
                "date": fields.Datetime.to_datetime(date), "ledger_amount": -change, "absorbed": False,
                "valued_qty": move._get_valued_qty(), "remaining_qty": move._get_valued_qty()})
        return created

    # ------------------------------------------------------------------
    # Which part of an exit already has its cost of sales (design v4, D5)
    # ------------------------------------------------------------------
    def _variance_costed_ratio(self, net_out):
        """(key, share of the exit whose cost of sales is already posted)."""
        self.ensure_one()
        if "raw_material_production_id" in self._fields and self.raw_material_production_id:
            return ("mrp", self.raw_material_production_id), 1.0
        line = self.sale_line_id
        if line:
            qty = line._variance_costed_qty()
            bom_line = self.bom_line_id if "bom_line_id" in self._fields else False
            if bom_line and bom_line.bom_id.type == "phantom" and bom_line.bom_id.product_qty:
                # the invoice counts kits, the move counts components
                qty *= bom_line.product_qty / bom_line.bom_id.product_qty
            return ("sale", line), (min(1.0, max(0.0, qty / net_out)) if net_out else 0.0)
        picking = self.picking_id
        if "pos_order_id" in picking._fields and picking.pos_order_id:
            order = picking.pos_order_id
            costed = order.session_id.state == "closed" or (order.account_move and order.account_move.state == "posted")
            return ("pos", order.session_id), (1.0 if costed else 0.0)
        return ("none", False), 0.0
