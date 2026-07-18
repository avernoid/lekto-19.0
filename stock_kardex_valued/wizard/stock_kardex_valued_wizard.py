import logging
from collections import defaultdict
from datetime import datetime, time

import pytz
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero

_logger = logging.getLogger(__name__)

# Advisory-lock namespace (arbitrary constant, paired with the user id so two runs
# of the same user serialize, D8/§8/§9).
_ADVISORY_LOCK_NS = 0x4B56  # "KV"

# source_rank orders same-date events: moves (0) BEFORE product.value revaluations (1).
# This is what reconciles with _run_average_batch (product.py:463); do NOT use -pv.id.
_RANK_MOVE = 0
_RANK_PV = 1

# Columns written by the bulk INSERT, in tuple order (§5.3 / §1.4: create_uid must be
# populated explicitly on a raw INSERT or the record rule + wipe-on-generate fail silently).
_INSERT_COLUMNS = [
    'company_id', 'currency_id', 'report_date_from', 'report_date_to',
    'product_tmpl_id', 'product_id', 'date', 'cost_method',
    'warehouse_id', 'location_id', 'location_dest_id', 'picking_type_id',
    'partner_id', 'product_categ_id', 'line_kind',
    'document', 'source_move_id', 'picking_id', 'invoice_id', 'bill_id',
    'ini_qty', 'ini_unit_cost', 'ini_value',
    'in_qty', 'in_unit_cost', 'in_value',
    'out_qty', 'out_unit_cost', 'out_value',
    'fin_qty', 'fin_unit_cost', 'fin_value',
    'bal_qty', 'bal_unit_cost', 'bal_value',
    'ple_bal_value', 'recon_delta',
    'create_uid', 'create_date', 'write_uid', 'write_date',
]


class StockKardexValuedWizard(models.TransientModel):
    _name = 'stock.kardex.valued.wizard'
    _description = 'Generate Valued Inventory Kardex'

    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company,
        help="Company to generate the Kardex for. The balance is computed at company "
             "level (one cost per product/company).")
    date_from = fields.Date(
        string='From', required=True, default=lambda self: self._default_date_from(),
        help="Start of the period. The opening balance is the state at the start of this "
             "date. Defaults to the first day of the previous month.")
    date_to = fields.Date(
        string='To', required=True, default=lambda self: self._default_date_to(),
        help="End of the period. The closing balance is the state at the end of this date. "
             "Must be on or after the 'From' date.")

    product_ids = fields.Many2many(
        'product.product', string='Products',
        help="Optional. Restrict the report to these products. Leave empty to include "
             "every product with movements in the company.")
    categ_ids = fields.Many2many(
        'product.category', string='Product Categories',
        help="Optional. Restrict the report to products in these categories (sub-categories "
             "included). Leave empty for no category filter.")

    # cost_method_filter (D4/§4): empty (all three unchecked) => all methods.
    cm_average = fields.Boolean(
        string='AVCO',
        help="Include Average-costed products. If Average, Standard and FIFO are all left "
             "unticked, ALL methods are included.")
    cm_standard = fields.Boolean(
        string='STD',
        help="Include Standard-costed products. If all three method boxes are unticked, "
             "ALL methods are included.")
    cm_fifo = fields.Boolean(
        string='FIFO',
        help="Include FIFO-costed products. If all three method boxes are unticked, ALL "
             "methods are included.")

    estimated_count = fields.Integer(
        string='N° Historical Events', compute='_compute_estimate',
        help="Estimated number of historical events (moves) that must be replayed for the "
             "selected scope. Drives the volume traffic-light.")
    estimated_hint = fields.Char(
        string='Volume', compute='_compute_estimate',
        help="Volume traffic-light: green runs now, amber still runs but suggests narrowing "
             "the scope, red is refused. Narrow by products/categories to reduce it.")

    # -- defaults ------------------------------------------------------------
    @api.model
    def _default_date_from(self):
        first_this_month = fields.Date.context_today(self).replace(day=1)
        return first_this_month - relativedelta(months=1)

    @api.model
    def _default_date_to(self):
        first_this_month = fields.Date.context_today(self).replace(day=1)
        return first_this_month - relativedelta(days=1)

    # -- estimate / traffic light -------------------------------------------
    @api.depends('company_id', 'date_from', 'date_to', 'product_ids', 'categ_ids',
                 'cm_average', 'cm_standard', 'cm_fifo')
    def _compute_estimate(self):
        for wiz in self:
            try:
                products = wiz._scope_products()
            except UserError:
                products = self.env['product.product']
            if not products:
                wiz.estimated_count = 0
                wiz.estimated_hint = _('No products in scope.')
                continue
            _dt_from, dt_to = wiz._period_bounds()
            # Semaphore over HISTORY, not the period (adversarial C3): the real cost is
            # replaying the previous history of the scoped products.
            count = self.env['stock.move'].with_context(active_test=False).search_count([
                ('product_id', 'in', products.ids),
                ('company_id', '=', wiz.company_id.id),
                ('state', '=', 'done'),
                ('date', '<=', dt_to),
                '|', '|', ('is_in', '=', True), ('is_out', '=', True), ('is_dropship', '=', True),
            ])
            sync_max, queue_max = wiz._thresholds()
            if count <= sync_max:
                hint = _('%(n)s events — will run now (synchronous).', n=count)
            elif count <= queue_max:
                hint = _('%(n)s events — heavy; will still run but consider narrowing '
                         'the products/categories.', n=count)
            else:
                hint = _('%(n)s events — too large (> %(max)s). Narrow the scope.',
                         n=count, max=queue_max)
            wiz.estimated_count = count
            wiz.estimated_hint = hint

    def _thresholds(self):
        icp = self.env['ir.config_parameter'].sudo()
        sync_max = int(icp.get_param('stock_kardex_valued.sync_max', 100000))
        queue_max = int(icp.get_param('stock_kardex_valued.queue_max', 1000000))
        return sync_max, queue_max

    # -- scope ---------------------------------------------------------------
    def _scope_products(self):
        """Products in scope for this run, at company level (D1).

        Base universe = products with at least one valued move in the company up to
        ``date_to`` (so we never replay products with no activity). Then apply the
        product / category / cost-method filters. ``lot_valuated`` products are excluded
        with a warning (D4/§5): their valuation is per lot, not by the AVCO/FIFO replay.
        """
        self.ensure_one()
        cid = self.company_id.id
        _dt_from, dt_to = self._period_bounds()
        base_domain = [
            ('company_id', '=', cid),
            ('state', '=', 'done'),
            ('date', '<=', dt_to),
            '|', '|', ('is_in', '=', True), ('is_out', '=', True), ('is_dropship', '=', True),
        ]
        if self.product_ids:
            base_domain.append(('product_id', 'in', self.product_ids.ids))
        groups = self.env['stock.move'].with_context(active_test=False)._read_group(
            base_domain, groupby=['product_id'])
        product_ids = [p.id for (p,) in groups]
        products = self.env['product.product'].with_context(active_test=False).browse(product_ids)
        if self.categ_ids:
            sel_ids = set(self.categ_ids.ids)

            def _in_categ(product):
                path = product.categ_id.parent_path or ''
                return bool(sel_ids & {int(x) for x in path.split('/') if x})

            products = products.filtered(_in_categ)
        # lot_valuated excluded with warning (D4).
        lot_valuated = products.filtered('lot_valuated')
        if lot_valuated:
            # Expected exclusion (D4), not an anomaly -> INFO, not WARNING.
            _logger.info(
                "stock.kardex.valued: excluding %s lot-valuated products (their valuation "
                "is per lot, not by the AVCO/FIFO replay): %s",
                len(lot_valuated), lot_valuated.ids)
        products = products - lot_valuated
        # cost-method filter (empty => all).
        wanted = self._wanted_methods()
        if wanted:
            products = products.with_company(cid).filtered(lambda p: p.cost_method in wanted)
        return products.with_company(cid)

    def _wanted_methods(self):
        wanted = set()
        if self.cm_average:
            wanted.add('average')
        if self.cm_standard:
            wanted.add('standard')
        if self.cm_fifo:
            wanted.add('fifo')
        return wanted  # empty => all

    # -- period bounds (D8: company tz frontier) -----------------------------
    def _tz(self):
        return self.env.context.get('tz') or self.env.user.tz or 'UTC'

    def _period_bounds(self):
        """Return (dt_from, dt_to) as naive UTC datetimes for the [date_from, date_to]
        range interpreted in the company/user timezone (D8). date_to is inclusive up to
        end-of-day local time."""
        self.ensure_one()
        if not self.date_from or not self.date_to:
            raise UserError(_("Please set both 'From' and 'To' dates."))
        if self.date_from > self.date_to:
            raise UserError(_("'From' date must be on or before the 'To' date."))
        tz = pytz.timezone(self._tz())
        dt_from_local = tz.localize(datetime.combine(self.date_from, time.min))
        dt_to_local = tz.localize(datetime.combine(self.date_to, time.max))
        dt_from = dt_from_local.astimezone(pytz.utc).replace(tzinfo=None)
        dt_to = dt_to_local.astimezone(pytz.utc).replace(tzinfo=None)
        return dt_from, dt_to

    # -- generate ------------------------------------------------------------
    def action_generate(self):
        self.ensure_one()
        products = self._scope_products()
        if not products:
            raise UserError(_("No valued products found for the selected scope."))

        # Volume guard over history (§9). Red => refuse.
        _dt_from, dt_to = self._period_bounds()
        count = self.env['stock.move'].with_context(active_test=False).search_count([
            ('product_id', 'in', products.ids),
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'done'),
            ('date', '<=', dt_to),
            '|', '|', ('is_in', '=', True), ('is_out', '=', True), ('is_dropship', '=', True),
        ])
        sync_max, queue_max = self._thresholds()
        if count > queue_max:
            raise UserError(_(
                "The selected scope spans %(n)s history events (> %(max)s). "
                "Please narrow the products or categories.", n=count, max=queue_max))
        if count > sync_max:
            _logger.warning(
                "stock.kardex.valued: heavy run (%s events) executed synchronously; "
                "consider narrowing the scope.", count)

        # Advisory lock per user: serialize concurrent runs of the same user (they share
        # the create_uid-scoped rows). Auto-released at commit.
        self.env.cr.execute("SELECT pg_advisory_xact_lock(%s, %s)",
                            (_ADVISORY_LOCK_NS, self.env.uid))
        # Anti-garbage: wipe this user's previous rows atomically with the new INSERT (§8).
        self.env.cr.execute("DELETE FROM stock_kardex_valued WHERE create_uid = %s",
                            (self.env.uid,))
        self.env['stock.kardex.valued'].invalidate_model()

        rows, fin_value_by_product = self._build_rows(products, _dt_from, dt_to)
        self._bulk_insert(rows)
        self._assert_reconciliation(products, fin_value_by_product, dt_to)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Valued Inventory Kardex'),
            'res_model': 'stock.kardex.valued',
            'view_mode': 'list,pivot',
            'domain': [('create_uid', '=', self.env.uid)],
            'context': {'search_default_group_product': 1},
        }

    # -- engine (§5) ---------------------------------------------------------
    def _build_rows(self, products, dt_from, dt_to):
        """Fetch the event universe once, group it by product, dispatch to the
        method-specific replay and materialize the period rows.

        NOTE on faithfulness: the valued quantity per move comes from the core
        ``move._get_valued_qty()`` (the exact source used by ``_run_average_batch``,
        product.py:483/502), fetched via a single batched ``search``. The cumulative
        recurrence is then replayed over plain Python dicts (D14) — that is where the
        audit report's O(n^2) ORM cost lived. We deliberately do NOT re-implement
        ``_get_valued_qty`` in raw SQL: core keeps it in Python and a SQL copy would
        diverge on consignment / returns / partial picks.
        """
        self.ensure_one()
        cid = self.company_id.id
        events_by_product = self._fetch_events(products, dt_to)

        rows = []
        fin_value_by_product = {}
        methods = self._product_methods(products)
        for product in products:
            method = methods.get(product.id, 'average')
            events = events_by_product.get(product.id, [])
            if method == 'fifo':
                prows, fin_value = self._replay_fifo(product, events, dt_from, dt_to)
            elif method == 'standard':
                prows, fin_value = self._replay_standard(product, events, dt_from, dt_to)
            else:
                prows, fin_value = self._replay_average(product, events, dt_from, dt_to)
            rows.extend(prows)
            fin_value_by_product[product.id] = fin_value
        return rows, fin_value_by_product

    def _product_methods(self, products):
        cid = self.company_id.id
        return {p.id: p.cost_method for p in products.with_company(cid)}

    def _fetch_events(self, products, dt_to):
        """One pass over stock.move + one over product.value; returns
        ``{product_id: [event_dict, ...]}`` sorted by (date, source_rank, id)."""
        cid = self.company_id.id
        events_by_product = defaultdict(list)

        moves = self.env['stock.move'].with_context(active_test=False).search([
            ('product_id', 'in', products.ids),
            ('company_id', '=', cid),
            ('state', '=', 'done'),
            ('date', '<=', dt_to),
            '|', '|', ('is_in', '=', True), ('is_out', '=', True), ('is_dropship', '=', True),
        ], order='product_id, date, id')
        for move in moves:
            picking = move.picking_id
            events_by_product[move.product_id.id].append({
                'kind': 'move',
                'date': move.date,
                'rank': _RANK_MOVE,
                'id': move.id,
                'valued_qty': move._get_valued_qty(),
                'value': move.value,
                'is_in': bool(move.is_in),
                'is_out': bool(move.is_out),
                'is_dropship': bool(move.is_dropship),
                'location_id': move.location_id.id,
                'location_dest_id': move.location_dest_id.id,
                'picking_type_id': move.picking_type_id.id,
                'picking_id': picking.id,
                'partner_id': (picking.partner_id.id if picking else False),
                'warehouse_id': (move.picking_type_id.warehouse_id.id if move.picking_type_id else False),
                'document': (picking.name if picking else False) or move.reference or _('Stock Move'),
            })

        pvs = self.env['product.value'].sudo().search([
            ('product_id', 'in', products.ids),
            ('move_id', '=', False),
            ('lot_id', '=', False),
            ('company_id', '=', cid),
            ('date', '<=', dt_to),
        ], order='product_id, date, id')
        for pv in pvs:
            events_by_product[pv.product_id.id].append({
                'kind': 'pv',
                'date': pv.date,
                'rank': _RANK_PV,
                'id': pv.id,
                'value': pv.value,
            })

        for pid in events_by_product:
            events_by_product[pid].sort(key=lambda e: (e['date'], e['rank'], e['id']))
        return events_by_product

    # -- row helpers ---------------------------------------------------------
    def _uc(self, value, qty):
        prec = self.env['decimal.precision'].precision_get('Product Unit')
        return value / qty if not float_is_zero(qty, precision_digits=prec) else 0.0

    def _base_row(self, product, ev=None, line_kind=False, document=False):
        return {
            'company_id': self.company_id.id,
            'currency_id': self.company_id.currency_id.id,
            'report_date_from': self.date_from,
            'report_date_to': self.date_to,
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_id': product.id,
            'date': (ev['date'] if ev else None),
            'cost_method': product.with_company(self.company_id).cost_method,
            'warehouse_id': (ev.get('warehouse_id') if ev else False) or False,
            'location_id': (ev.get('location_id') if ev else False) or False,
            'location_dest_id': (ev.get('location_dest_id') if ev else False) or False,
            'picking_type_id': (ev.get('picking_type_id') if ev else False) or False,
            'partner_id': (ev.get('partner_id') if ev else False) or False,
            'product_categ_id': product.categ_id.id,
            'line_kind': line_kind,
            'document': document or (ev.get('document') if ev else False) or False,
            'source_move_id': (ev['id'] if ev and ev['kind'] == 'move' else False),
            'picking_id': (ev.get('picking_id') if ev else False) or False,
            'invoice_id': False,
            'bill_id': False,
            'ini_qty': 0.0, 'ini_unit_cost': 0.0, 'ini_value': 0.0,
            'in_qty': 0.0, 'in_unit_cost': 0.0, 'in_value': 0.0,
            'out_qty': 0.0, 'out_unit_cost': 0.0, 'out_value': 0.0,
            'fin_qty': 0.0, 'fin_unit_cost': 0.0, 'fin_value': 0.0,
            'bal_qty': 0.0, 'bal_unit_cost': 0.0, 'bal_value': 0.0,
            'ple_bal_value': 0.0, 'recon_delta': 0.0,
        }

    def _row_is_empty(self, row):
        prec = self.env['decimal.precision'].precision_get('Product Unit')
        return (float_is_zero(row['in_qty'], precision_digits=prec)
                and float_is_zero(row['out_qty'], precision_digits=prec)
                and self.company_id.currency_id.is_zero(row['in_value'])
                and self.company_id.currency_id.is_zero(row['out_value']))

    def _finalize(self, product, prows, opening, closing):
        """Attach single-cell opening/closing (ini_*/fin_*) and a backup 'Opening balance'
        row when the period has no movements (D9: only if qty!=0 OR value!=0)."""
        op_qty, op_value, op_uc = opening
        cl_qty, cl_value, cl_uc = closing
        curr = self.company_id.currency_id
        prec = self.env['decimal.precision'].precision_get('Product Unit')
        if not prows:
            if float_is_zero(op_qty, precision_digits=prec) and curr.is_zero(op_value):
                return []
            row = self._base_row(product, line_kind='opening', document=_('Opening balance'))
            row.update({
                'ini_qty': op_qty, 'ini_value': op_value, 'ini_unit_cost': op_uc,
                'fin_qty': op_qty, 'fin_value': op_value, 'fin_unit_cost': op_uc,
                'bal_qty': op_qty, 'bal_value': op_value, 'bal_unit_cost': op_uc,
                'ple_bal_value': op_value, 'recon_delta': op_value - op_value,
            })
            return [row]
        prows[0].update({'ini_qty': op_qty, 'ini_value': op_value, 'ini_unit_cost': op_uc})
        prows[-1].update({'fin_qty': cl_qty, 'fin_value': cl_value, 'fin_unit_cost': cl_uc})
        return prows

    # -- AVERAGE replay (copies the authoritative _run_average_batch recurrence,
    #    product.py:481-509; product.value events re-base as in _compute_cumulative_fields) --
    def _replay_average(self, product, events, dt_from, dt_to):
        qty = value = avco = 0.0
        ple_bal = 0.0
        opening = None
        prows = []
        for ev in events:
            in_period = dt_from <= ev['date'] <= dt_to
            if opening is None and ev['date'] >= dt_from:
                opening = (qty, value, avco)
            if ev['kind'] == 'move':
                row = self._base_row(product, ev)
                before_value = value
                did_in = did_out = False
                if ev['is_in'] or ev['is_dropship']:
                    in_qty = ev['valued_qty']
                    in_value_raw = (avco * in_qty) if ev['is_dropship'] else ev['value']
                    prev_qty = qty
                    qty += in_qty
                    if prev_qty > 0:
                        value += in_value_raw
                        avco = value / qty if qty else avco
                    else:  # from-negative: re-base on the incoming unit value
                        avco = in_value_raw / in_qty if in_qty else avco
                        value = avco * qty
                    after_in_value = value
                    row['in_qty'] = in_qty
                    row['in_value'] = after_in_value - before_value
                    row['in_unit_cost'] = self._uc(row['in_value'], in_qty)
                    if ev['is_in']:
                        ple_bal += ev['value']
                    did_in = True
                if ev['is_out'] or ev['is_dropship']:
                    out_qty = ev['valued_qty']
                    out_value = out_qty * avco
                    value -= out_value
                    qty -= out_qty
                    row['out_qty'] = out_qty
                    row['out_value'] = out_value
                    row['out_unit_cost'] = avco
                    if ev['is_out']:
                        ple_bal -= ev['value']
                    did_out = True
                row['line_kind'] = 'out' if (did_out and not did_in) else 'in'
                if ev['is_dropship']:
                    row['line_kind'] = 'out'
            else:  # product.value revaluation
                row = self._base_row(product, ev, line_kind='revaluation',
                                     document=_('Revaluation'))
                nv = ev['value']
                delta = nv * qty - value
                value = nv * qty
                avco = nv
                row['in_value'] = delta
            row['bal_qty'] = qty
            row['bal_value'] = value
            row['bal_unit_cost'] = avco
            row['ple_bal_value'] = ple_bal
            row['recon_delta'] = value - ple_bal
            if in_period and not self._row_is_empty(row):
                prows.append(row)
        if opening is None:
            opening = (qty, value, avco)
        closing = (qty, value, avco)
        return self._finalize(product, prows, opening, closing), value

    # -- STANDARD replay (§5.7, D16): value = qty * std_vigente ---------------
    def _replay_standard(self, product, events, dt_from, dt_to):
        std = product.with_company(self.company_id).standard_price
        qty = 0.0
        ple_bal = 0.0
        opening = None
        prows = []
        for ev in events:
            in_period = dt_from <= ev['date'] <= dt_to
            if opening is None and ev['date'] >= dt_from:
                opening = (qty, qty * std, std)
            if ev['kind'] == 'move':
                row = self._base_row(product, ev)
                did_in = did_out = False
                if ev['is_in'] or ev['is_dropship']:
                    in_qty = ev['valued_qty']
                    qty += in_qty
                    row['in_qty'] = in_qty
                    row['in_value'] = std * in_qty
                    row['in_unit_cost'] = std
                    if ev['is_in']:
                        ple_bal += ev['value']
                    did_in = True
                if ev['is_out'] or ev['is_dropship']:
                    out_qty = ev['valued_qty']
                    qty -= out_qty
                    row['out_qty'] = out_qty
                    row['out_value'] = std * out_qty
                    row['out_unit_cost'] = std
                    if ev['is_out']:
                        ple_bal -= ev['value']
                    did_out = True
                row['line_kind'] = 'out' if (did_out and not did_in) else 'in'
                if ev['is_dropship']:
                    row['line_kind'] = 'out'
            else:  # standard price change (revaluation)
                row = self._base_row(product, ev, line_kind='revaluation',
                                     document=_('Revaluation'))
                nv = ev['value']
                delta = (nv - std) * qty
                std = nv
                row['in_value'] = delta
            row['bal_qty'] = qty
            row['bal_value'] = qty * std
            row['bal_unit_cost'] = std
            row['ple_bal_value'] = ple_bal
            row['recon_delta'] = (qty * std) - ple_bal
            if in_period and not self._row_is_empty(row):
                prows.append(row)
        if opening is None:
            opening = (qty, qty * std, std)
        closing = (qty, qty * std, std)
        return self._finalize(product, prows, opening, closing), qty * std

    # -- FIFO replay (§5.6, D11): layer queue, replicates _run_fifo -----------
    def _replay_fifo(self, product, events, dt_from, dt_to):
        layers = []  # list of [remaining_qty, unit_cost], oldest first
        bal_qty = bal_value = 0.0
        last_unit_cost = product.with_company(self.company_id).standard_price
        ple_bal = 0.0
        opening = None
        prows = []
        for ev in events:
            in_period = dt_from <= ev['date'] <= dt_to
            if opening is None and ev['date'] >= dt_from:
                opening = (bal_qty, bal_value, self._uc(bal_value, bal_qty))
            if ev['kind'] != 'move':
                # FIFO does not revalue via product.value (D11); ignore.
                continue
            row = self._base_row(product, ev)
            did_in = did_out = False
            if ev['is_in'] or ev['is_dropship']:
                in_qty = ev['valued_qty']
                in_value = ev['value']
                unit = self._uc(in_value, in_qty) or last_unit_cost
                if in_qty:
                    layers.append([in_qty, unit])
                    last_unit_cost = unit
                bal_qty += in_qty
                bal_value += in_value
                row['in_qty'] = in_qty
                row['in_value'] = in_value
                row['in_unit_cost'] = unit
                if ev['is_in']:
                    ple_bal += ev['value']
                did_in = True
            if ev['is_out'] or ev['is_dropship']:
                out_qty = ev['valued_qty']
                remaining = out_qty
                out_value = 0.0
                while remaining > 0 and layers:
                    layer = layers[0]
                    take = min(layer[0], remaining)
                    out_value += take * layer[1]
                    layer[0] -= take
                    remaining -= take
                    last_unit_cost = layer[1]
                    if layer[0] <= 0:
                        layers.pop(0)
                if remaining > 0:  # stock negative: extrapolate last known cost
                    out_value += remaining * last_unit_cost
                bal_qty -= out_qty
                bal_value -= out_value
                row['out_qty'] = out_qty
                row['out_value'] = out_value
                row['out_unit_cost'] = self._uc(out_value, out_qty)
                if ev['is_out']:
                    ple_bal -= ev['value']
                did_out = True
            row['line_kind'] = 'out' if (did_out and not did_in) else 'in'
            if ev['is_dropship']:
                row['line_kind'] = 'out'
            row['bal_qty'] = bal_qty
            row['bal_value'] = bal_value
            row['bal_unit_cost'] = self._uc(bal_value, bal_qty)
            row['ple_bal_value'] = ple_bal
            row['recon_delta'] = bal_value - ple_bal
            if in_period and not self._row_is_empty(row):
                prows.append(row)
        if opening is None:
            opening = (bal_qty, bal_value, self._uc(bal_value, bal_qty))
        closing = (bal_qty, bal_value, self._uc(bal_value, bal_qty))
        return self._finalize(product, prows, opening, closing), bal_value

    # -- persistence ---------------------------------------------------------
    def _bulk_insert(self, rows):
        if not rows:
            return
        now = fields.Datetime.now()
        uid = self.env.uid
        cols_sql = ", ".join(_INSERT_COLUMNS)
        template = "(" + ",".join(["%s"] * len(_INSERT_COLUMNS)) + ")"
        # m2o / char columns default to NULL when falsy; numeric columns to 0.0.
        m2o_char = {
            'company_id', 'currency_id', 'report_date_from', 'report_date_to',
            'product_tmpl_id', 'product_id', 'date', 'cost_method', 'warehouse_id',
            'location_id', 'location_dest_id', 'picking_type_id', 'partner_id',
            'product_categ_id', 'line_kind', 'document', 'source_move_id', 'picking_id',
            'invoice_id', 'bill_id',
        }
        batch = 5000
        for i in range(0, len(rows), batch):
            chunk = rows[i:i + batch]
            tuples = []
            for r in chunk:
                r['create_uid'] = uid
                r['create_date'] = now
                r['write_uid'] = uid
                r['write_date'] = now
                tuples.append(tuple(
                    (r.get(c) or None) if c in m2o_char else r.get(c, 0.0)
                    for c in _INSERT_COLUMNS))
            values_sql = b",".join(self.env.cr.mogrify(template, t) for t in tuples).decode()
            self.env.cr.execute(
                "INSERT INTO stock_kardex_valued (%s) VALUES %s" % (cols_sql, values_sql))
        self.env['stock.kardex.valued'].invalidate_model()

    # -- D17 reconciliation invariant ----------------------------------------
    def _assert_reconciliation(self, products, fin_value_by_product, dt_to):
        """For a sample of products, assert fin_value == total_value(to_date) at company
        level (D17). Logs a warning on divergence; the tests assert it hard."""
        cid = self.company_id.id
        curr = self.company_id.currency_id
        sample = products[:50]
        diverged = []
        for product in sample.with_company(cid).with_context(
                allowed_company_ids=[cid], to_date=dt_to):
            ledger = fin_value_by_product.get(product.id, 0.0)
            gl = product.total_value
            if float_compare(ledger, gl, precision_rounding=curr.rounding) != 0:
                diverged.append((product.id, ledger, gl))
        if diverged:
            _logger.warning(
                "stock.kardex.valued: %s product(s) diverged from total_value (GL): %s",
                len(diverged), diverged[:10])
        return diverged
