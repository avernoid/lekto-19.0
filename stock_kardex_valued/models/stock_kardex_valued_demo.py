import logging
from datetime import datetime

from odoo import api, models

_logger = logging.getLogger(__name__)

# Year every demo movement happens in. Kept in one place so the whole timeline can be
# shifted if needed. Activity is spread across every month Jan-Jun so that ANY period
# the user picks (including the wizard default = previous month) shows real movements,
# not just carried-forward opening balances.
_YEAR = 2026

# Marker so the whole generation runs at most once (it is invoked from a demo
# <function> that would otherwise re-run on every module update).
_DEMO_FLAG = 'stock_kardex_valued.demo_generated'


# ---------------------------------------------------------------------------
# A dense, every-month movement pattern: SEVERAL movements per month (3 receipts + 3
# deliveries on different days) across Jan-Jun = 36 events. Used by the "busy" single
# products and by every variant so each month is visibly busy and the running average /
# FIFO queue / standard value can be followed over many rows. Receipt costs drift both
# month to month and within the month, so AVCO/FIFO show many distinct unit costs.
# ``seed`` shifts quantities so sibling variants of the same template differ visibly;
# receipts always exceed deliveries so stock stays positive. For STANDARD products the
# receipt cost is ignored by the engine (value = qty x std); the density still holds.
# ---------------------------------------------------------------------------
def _monthly_pattern(base_cost, seed=0):
    in_days = [3, 13, 23]
    out_days = [8, 18, 27]
    in_qty = [12, 10, 14]
    out_qty = [5, 7, 6]
    steps = []
    for month_idx, month in enumerate([1, 2, 3, 4, 5, 6]):
        month_factor = 1.0 + 0.03 * month_idx
        for slot in range(3):
            cost = round(base_cost * month_factor * (1.0 + 0.02 * slot), 2)
            steps.append(('in', '%02d-%02d' % (month, in_days[slot]),
                         in_qty[slot] + seed, cost))
            steps.append(('out', '%02d-%02d' % (month, out_days[slot]),
                         out_qty[slot] + (seed // 2)))
    return steps


# ---------------------------------------------------------------------------
# Scenario timelines for single-variant products. Each product (referenced by its XML
# id) is a list of steps executed in order; every step is also back-dated to the given
# day so the report replays a realistic history. Step grammar:
#   ('in',    'MM-DD', qty, unit_cost)  -> validated receipt (supplier -> stock)
#   ('out',   'MM-DD', qty)             -> validated delivery (stock -> customer)
#   ('drop',  'MM-DD', qty, unit_cost)  -> dropship (supplier -> customer, value-neutral)
#   ('reval', 'MM-DD', new_unit_cost)   -> AVCO manual cost adjustment (product.value)
#   ('std',   'MM-DD', new_std)         -> Standard price change (product.value)
# The trailing comment on each product explains what it is meant to teach.
# ---------------------------------------------------------------------------
_SCENARIOS = {
    # --- AVCO ---------------------------------------------------------------
    # Moving average recomputes on every receipt; outs leave at the running average.
    'product_avco_basic': [
        ('in',  '01-05', 10, 10.0),   # avg 10
        ('in',  '01-12', 10, 20.0),   # avg 15
        ('out', '01-20', 5),          # COGS 5 @ 15 = 75
        ('out', '02-03', 8),          # COGS 8 @ 15 = 120
    ],
    # A manual cost adjustment re-bases the average and emits a Revaluation line.
    # This is where the naive PLE ledger (sum of move.value) diverges from the GL:
    # watch recon_delta become non-zero.
    'product_avco_reval': [
        ('in',    '01-08', 100, 5.0),  # value 500, avg 5
        ('reval', '01-25', 7.0),       # re-base to 7 -> +200, value 700
        ('out',   '02-10', 30),        # COGS 30 @ 7 = 210
    ],
    # Selling before buying drives stock negative; the next receipt re-bases the average.
    'product_avco_negative': [
        ('out', '01-15', 5),           # qty -5
        ('in',  '01-22', 10, 12.0),    # re-base @ 12
        ('out', '02-05', 2),
    ],
    # Freight/landed cost embedded in the receipt value: the unit cost arrives already
    # loaded (base 10 + freight 2 = 12), exactly as the report reads move.value.
    'product_avco_landed': [
        ('in',  '01-10', 20, 12.0),    # base 200 + landed 40 = 240, avg 12
        ('out', '01-28', 8),           # COGS 8 @ 12 = 96
    ],
    # Dropship supplier -> customer: an in and an out of equal value cancel out; the
    # on-hand balance is untouched.
    'product_avco_dropship': [
        ('in',   '01-17', 10, 10.0),
        ('drop', '01-30', 4, 10.0),    # value-neutral
    ],
    # Two receipts far apart: run the wizard month by month to see closing(N) = opening(N+1).
    'product_avco_multiperiod': [
        ('in',  '02-05', 10, 10.0),    # Feb closing 100
        ('in',  '04-08', 10, 10.0),    # Apr closing 200
    ],
    # A busy item so the running balance column really moves. Pure moves only: the
    # moving average is re-derived on every receipt and every out leaves at that
    # average (manual cost adjustments are demonstrated by product_avco_reval, which
    # keeps a single revaluation followed only by outs so it stays GL-reconciled).
    'product_avco_busy': [
        ('in',  '01-03', 40, 15.0),
        ('out', '01-14', 12),
        ('in',  '01-27', 20, 18.0),
        ('out', '02-11', 25),
        ('in',  '03-04', 30, 16.0),
        ('out', '03-22', 18),
        ('out', '05-09', 20),
        ('in',  '06-02', 15, 19.0),
    ],

    # --- FIFO ---------------------------------------------------------------
    # Layer queue: 10@10 then 10@20, sell 15 -> COGS 100+100, remaining 5 @ 20.
    'product_fifo_basic': [
        ('in',  '01-06', 10, 10.0),
        ('in',  '01-13', 10, 20.0),
        ('out', '01-21', 15),          # 10@10 + 5@20 = 200
        ('out', '02-04', 2),           # 2 @ 20 = 40
    ],
    # Out with no stock: FIFO extrapolates the last known / standard cost.
    'product_fifo_negative': [
        ('out', '01-16', 5),           # no layers -> 5 @ std 10 = 50
        ('in',  '01-23', 8, 15.0),
        ('out', '02-06', 1),
    ],
    # Several layers partially consumed by a single out.
    'product_fifo_multilayer': [
        ('in',  '01-07', 5, 8.0),
        ('in',  '01-14', 5, 9.0),
        ('in',  '01-19', 5, 11.0),
        ('out', '01-26', 12),          # 5@8 + 5@9 + 2@11 = 107
        ('out', '02-08', 1),
    ],
    'product_fifo_busy': [
        ('in',  '01-04', 30, 20.0),
        ('in',  '01-18', 20, 22.0),
        ('out', '01-29', 25),
        ('in',  '02-12', 15, 24.0),
        ('out', '03-05', 30),
        ('out', '04-10', 5),
        ('in',  '05-06', 25, 21.0),
        ('out', '06-03', 12),
    ],

    # --- STANDARD -----------------------------------------------------------
    # Value is always qty x standard price.
    'product_std_basic': [
        ('in',  '01-09', 50, 10.0),    # receipts valued at std 10
        ('out', '01-24', 20),          # COGS 20 @ 10 = 200
    ],
    # A mid-period standard price change emits a Revaluation line for the on-hand qty.
    'product_std_change': [
        ('in',  '01-11', 40, 10.0),    # 40 @ 10
        ('std', '01-27', 13.0),        # revalue on-hand: (13-10) * 40 = +120
        ('out', '02-09', 15),          # COGS 15 @ 13 = 195
    ],
    'product_std_busy': [
        ('in',  '01-08', 60, 25.0),
        ('out', '01-21', 20),
        ('in',  '02-14', 40, 25.0),
        ('std', '03-02', 28.0),
        ('out', '03-19', 35),
        ('in',  '04-25', 30, 28.0),
        ('out', '05-30', 40),
    ],
}

# Busy items with activity in EVERY month (Jan-Jun) so any period is populated and the
# per-method engines can be followed over a dozen rows each. For the AVCO / FIFO ones
# the drifting receipt cost is visible; for the standard one the value stays qty x std.
_SCENARIOS['product_avco_month'] = _monthly_pattern(15.0, seed=0)
_SCENARIOS['product_fifo_month'] = _monthly_pattern(30.0, seed=1)
_SCENARIOS['product_std_month'] = _monthly_pattern(25.0, seed=2)

# ---------------------------------------------------------------------------
# Multi-variant templates: (template_xml_id, [(attribute value name, base cost), ...]).
# Every variant gets the dense monthly pattern (12 rows) so the canonical
# Template -> Variant grouping of the report can be studied with real data: expand a
# template to see each size accumulate its own balance, and the template header
# aggregates the additive columns. AVCO/FIFO variants carry a different cost per size;
# the standard template keeps one std across sizes (value = qty x std).
# ---------------------------------------------------------------------------
_VARIANT_TEMPLATES = [
    ('tmpl_var_avco', [('S', 20.0), ('M', 24.0), ('L', 28.0)]),
    ('tmpl_var_fifo', [('S', 30.0), ('M', 34.0), ('L', 38.0)]),
    ('tmpl_var_std',  [('S', 15.0), ('M', 17.0), ('L', 19.0)]),
]


class StockKardexValuedDemo(models.AbstractModel):
    """Programmatic generator for the didactic demo (valued stock history).

    Valued moves must go through the real confirm/pick/validate flow so Odoo computes
    ``move.value`` and ``product.value`` the way it does in production; that cannot be
    expressed as flat XML. This abstract model is invoked once from the demo data via a
    ``<function>`` tag and is idempotent (guarded by an ``ir.config_parameter`` flag).
    """
    _name = 'stock.kardex.valued.demo'
    _description = 'Valued Kardex demo data generator'

    # -- entry point (called from data/demo/stock_kardex_valued_demo.xml) -----
    @api.model
    def _generate_demo_data(self):
        icp = self.env['ir.config_parameter'].sudo()
        if icp.get_param(_DEMO_FLAG):
            return  # already generated on a previous install/update

        company = self.env.ref('base.main_company', raise_if_not_found=False)
        if not company:
            return
        warehouse = self.env['stock.warehouse'].search(
            [('company_id', '=', company.id)], limit=1)
        if not warehouse:
            _logger.info("stock.kardex.valued demo: no warehouse for %s, skipped.", company.name)
            return

        env = self.sudo().with_company(company).with_context(
            allowed_company_ids=[company.id]).env
        ctx = {
            'company': company,
            'warehouse': warehouse,
            'stock_loc': warehouse.lot_stock_id,
            'supplier_loc': env.ref('stock.stock_location_suppliers'),
            'customer_loc': env.ref('stock.stock_location_customers'),
            'vendor': env.ref('stock_kardex_valued.partner_demo_vendor'),
            'customer': env.ref('stock_kardex_valued.partner_demo_customer'),
        }
        gen = self.sudo().with_company(company).with_context(allowed_company_ids=[company.id])

        # 1) single-variant scenarios (focused lessons + monthly busy items)
        for xmlid, steps in _SCENARIOS.items():
            product = env.ref('stock_kardex_valued.%s' % xmlid, raise_if_not_found=False)
            if not product:
                continue
            gen._run_scenario(ctx, product.with_company(company), steps)

        # 2) multi-variant templates (Template -> Variant grouping demo)
        n_variants = 0
        for tmpl_xmlid, variants in _VARIANT_TEMPLATES:
            template = env.ref('stock_kardex_valued.%s' % tmpl_xmlid, raise_if_not_found=False)
            if not template:
                continue
            for seed, (value_name, base_cost) in enumerate(variants):
                variant = self._variant_by_value(template, value_name)
                if not variant:
                    continue
                variant = variant.with_company(company)
                # Standard products value at qty x standard_price; the template std does
                # NOT propagate to auto-generated variants, so set it per variant (else
                # value stays 0). Back-date the resulting product.value to before the
                # period so the wizard and the GL agree on the in-force cost.
                if variant.cost_method == 'standard':
                    self._set_variant_std(ctx, variant, base_cost)
                gen._run_scenario(ctx, variant, _monthly_pattern(base_cost, seed))
                n_variants += 1

        icp.set_param(_DEMO_FLAG, '1')
        _logger.info("stock.kardex.valued demo: generated %s scenarios + %s variants.",
                    len(_SCENARIOS), n_variants)

    def _set_variant_std(self, ctx, product, std):
        """Set a standard-cost variant's price and anchor it before the demo period so
        that ``_get_last_product_value`` (GL) and the wizard both see the same std."""
        product.sudo().standard_price = std
        pv = self.env['product.value'].sudo().search([
            ('product_id', '=', product.id),
            ('move_id', '=', False),
            ('company_id', '=', ctx['company'].id),
        ], order='id desc', limit=1)
        if pv:
            pv.write({'date': datetime(_YEAR - 1, 12, 1, 0, 0)})

    # -- variant resolution --------------------------------------------------
    def _variant_by_value(self, template, value_name):
        """Return the template's variant carrying the given attribute value (e.g. 'S')."""
        for variant in template.product_variant_ids:
            if value_name in variant.product_template_variant_value_ids.mapped('name'):
                return variant
        return False

    # -- scenario interpreter ------------------------------------------------
    def _run_scenario(self, ctx, product, steps):
        for step in steps:
            kind, day = step[0], step[1]
            date = self._date(day)
            if kind == 'in':
                self._make_in(ctx, product, step[2], step[3], date)
            elif kind == 'out':
                self._make_out(ctx, product, step[2], date)
            elif kind == 'drop':
                self._make_in(ctx, product, step[2], step[3], date,
                             dest=ctx['customer_loc'])
            elif kind == 'reval':
                self._make_avco_reval(ctx, product, step[2], date)
            elif kind == 'std':
                self._make_std_change(ctx, product, step[2], date)

    def _date(self, day):
        month, dom = (int(x) for x in day.split('-'))
        return datetime(_YEAR, month, dom, 12, 0, 0)

    # -- move builders (mirror stock_account test helpers, production-safe) --
    def _make_in(self, ctx, product, qty, unit_cost, date, dest=None):
        picking = self.env['stock.picking'].create({
            'picking_type_id': ctx['warehouse'].in_type_id.id,
            'location_id': ctx['supplier_loc'].id,
            'location_dest_id': (dest or ctx['stock_loc']).id,
            'partner_id': ctx['vendor'].id,
            'origin': 'DEMO Receipt',
        })
        move = self.env['stock.move'].create({
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': qty,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'picking_type_id': picking.picking_type_id.id,
            'picking_id': picking.id,
            'price_unit': unit_cost,
            'value_manual': unit_cost * qty,
        })
        self._validate(picking, move, qty)
        self._backdate(move, date)
        return move

    def _make_out(self, ctx, product, qty, date):
        picking = self.env['stock.picking'].create({
            'picking_type_id': ctx['warehouse'].out_type_id.id,
            'location_id': ctx['stock_loc'].id,
            'location_dest_id': ctx['customer_loc'].id,
            'partner_id': ctx['customer'].id,
            'origin': 'DEMO Delivery',
        })
        move = self.env['stock.move'].create({
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': qty,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'picking_type_id': picking.picking_type_id.id,
            'picking_id': picking.id,
        })
        self._validate(picking, move, qty)
        self._backdate(move, date)
        return move

    def _validate(self, picking, move, qty):
        move._action_confirm()
        move._action_assign()
        move.quantity = qty
        move.picked = True
        res = picking.button_validate()
        if isinstance(res, dict) and res.get('res_model'):
            # A confirmation wizard slipped through (immediate transfer / backorder).
            # Since the move is fully picked, finalize it directly.
            move._action_done()

    def _backdate(self, move, date):
        # Force the historical timestamp (Odoo stamps 'now' on validation). Done right
        # after each move so the next event of the same product is already in the past,
        # keeping the per-product valuation replay in chronological order.
        move.write({'date': date})
        if move.picking_id:
            move.picking_id.write({'date_done': date, 'scheduled_date': date})

    # -- revaluations --------------------------------------------------------
    def _make_avco_reval(self, ctx, product, new_unit_cost, date):
        pv = self.env['product.value'].sudo().create({
            'product_id': product.id,
            'company_id': ctx['company'].id,
            'value': new_unit_cost,
            'description': 'DEMO cost adjustment',
        })
        pv.write({'date': date})
        return pv

    def _make_std_change(self, ctx, product, new_std, date):
        # Writing standard_price creates a product.value automatically (core
        # _change_standard_price); back-date it so the change lands inside the period.
        product.with_company(ctx['company']).sudo().standard_price = new_std
        pv = self.env['product.value'].sudo().search([
            ('product_id', '=', product.id),
            ('move_id', '=', False),
            ('company_id', '=', ctx['company'].id),
        ], order='id desc', limit=1)
        pv.write({'date': date})
        return pv
