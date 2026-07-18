from datetime import datetime, time

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.stock_account.tests.common import TestStockValuationCommon


@tagged('post_install', '-at_install')
class TestStockKardexValued(TestStockValuationCommon):
    """Tests for the valued Kardex (§12 of the design).

    The golden invariant (D17) is ``closing == product.total_value(to_date)`` at company
    level for the three cost methods; several tests assert it directly.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cid = cls.company.id
        cls.KV = cls.env['stock.kardex.valued']
        cls.Wizard = cls.env['stock.kardex.valued.wizard']

    # ------------------------------------------------------------------ utils
    def _set_date(self, records, dt):
        """Force the historical date of moves / product.values (Odoo resets to now)."""
        records.write({'date': dt})

    def _frontier(self, date_to):
        """Naive-UTC end-of-day frontier for a Date, matching the wizard's UTC tz path."""
        return datetime.combine(date_to, time.max)

    def _gl(self, product, to_dt):
        """The GL truth: total_value at company level at ``to_dt`` (must pass a datetime
        so the core does the real replay instead of the qty*standard_price shortcut)."""
        return product.with_company(self.company).with_context(
            allowed_company_ids=[self.cid], to_date=to_dt).total_value

    def _run(self, date_from, date_to, user=None, **vals):
        wiz = self.Wizard.with_context(tz='UTC')
        if user:
            wiz = wiz.with_user(user)
        wiz = wiz.create({
            'company_id': self.cid,
            'date_from': date_from,
            'date_to': date_to,
            **vals,
        })
        wiz.action_generate()
        domain = [('create_uid', '=', (user or self.env.user).id)]
        return self.KV.search(domain)

    def _closing(self, rows, product):
        pr = rows.filtered(lambda r: r.product_id == product)
        return sum(pr.mapped('fin_value')), sum(pr.mapped('fin_qty'))

    def _opening(self, rows, product):
        pr = rows.filtered(lambda r: r.product_id == product)
        return sum(pr.mapped('ini_value')), sum(pr.mapped('ini_qty'))

    # ------------------------------------------------------------------ tests
    def test_01_reconciliation_average(self):
        """AVCO in/out re-derived from the average reconciles with total_value (GL)."""
        d1 = datetime(2024, 1, 5, 12, 0)
        d2 = datetime(2024, 1, 10, 12, 0)
        d3 = datetime(2024, 1, 20, 12, 0)
        p = self.product_avco
        self._set_date(self._make_in_move(p, 10, unit_cost=10), d1)   # avg 10
        self._set_date(self._make_in_move(p, 10, unit_cost=20), d2)   # avg 15
        self._set_date(self._make_out_move(p, 5), d3)                 # out 5 @ 15 -> 75

        date_to = fields.Date.to_date('2024-01-31')
        rows = self._run(fields.Date.to_date('2024-01-01'), date_to)
        close_val, close_qty = self._closing(rows, p)
        self.assertAlmostEqual(close_qty, 15.0, places=2)
        self.assertAlmostEqual(close_val, 225.0, places=2)  # 300 - 75
        self.assertAlmostEqual(close_val, self._gl(p, self._frontier(date_to)), places=2)

    def test_02_reconciliation_revaluation(self):
        """A manual product.value revaluation re-bases the average and emits a
        revaluation line; the closing reconciles with total_value (GL). Covers the
        pid=1143 pattern where the GL only agrees once revaluations are replayed."""
        d1 = datetime(2024, 2, 5, 12, 0)
        d2 = datetime(2024, 2, 10, 12, 0)
        p = self.product_avco
        self._set_date(self._make_in_move(p, 10, unit_cost=10), d1)  # value 100, avg 10
        pv = self.env['product.value'].create({
            'product_id': p.id, 'company_id': self.cid, 'value': 15.0,
        })
        self._set_date(pv, d2)  # revalue unit cost -> 15 => value 150, delta +50

        date_to = fields.Date.to_date('2024-02-28')
        rows = self._run(fields.Date.to_date('2024-02-01'), date_to)
        close_val, _q = self._closing(rows, p)
        self.assertAlmostEqual(close_val, 150.0, places=2)
        self.assertAlmostEqual(close_val, self._gl(p, self._frontier(date_to)), places=2)
        reval = rows.filtered(lambda r: r.line_kind == 'revaluation')
        self.assertTrue(reval, "A revaluation line must be emitted")
        self.assertAlmostEqual(sum(reval.mapped('in_value')), 50.0, places=2)  # (15-10)*10

    def test_03_from_negative(self):
        """Out before In (from-negative): the In re-bases the average and the row sums."""
        d1 = datetime(2024, 3, 5, 12, 0)
        d2 = datetime(2024, 3, 10, 12, 0)
        p = self.product_avco
        self._set_date(self._make_out_move(p, 5), d1)               # qty -5
        self._set_date(self._make_in_move(p, 10, unit_cost=12), d2)  # re-base

        date_to = fields.Date.to_date('2024-03-31')
        rows = self._run(fields.Date.to_date('2024-03-01'), date_to)
        close_val, close_qty = self._closing(rows, p)
        self.assertAlmostEqual(close_qty, 5.0, places=2)
        self.assertAlmostEqual(close_val, self._gl(p, self._frontier(date_to)), places=2)
        # The running balance must equal opening + in - out across the kept rows.
        pr = rows.filtered(lambda r: r.product_id == p).sorted(lambda r: (r.date, r.id))
        self.assertAlmostEqual(pr[-1].bal_value, close_val, places=2)

    def test_04_landed_cost_embedded(self):
        """LC is embedded in move.value at receipt (D5): outs re-derive from the
        average-with-LC and telescope to the GL. Simulated by an in move whose value
        already carries the extra (as core does via _set_value)."""
        d1 = datetime(2024, 4, 5, 12, 0)
        d2 = datetime(2024, 4, 20, 12, 0)
        p = self.product_avco
        # 10 units, base 10 + 20 landed => move.value 120 => avg 12
        self._set_date(self._make_in_move(p, 10, unit_cost=12), d1)
        self._set_date(self._make_out_move(p, 4), d2)  # 4 @ 12 = 48

        date_to = fields.Date.to_date('2024-04-30')
        rows = self._run(fields.Date.to_date('2024-04-01'), date_to)
        close_val, close_qty = self._closing(rows, p)
        self.assertAlmostEqual(close_qty, 6.0, places=2)
        self.assertAlmostEqual(close_val, 72.0, places=2)  # 120 - 48
        self.assertAlmostEqual(close_val, self._gl(p, self._frontier(date_to)), places=2)

    def test_05_dropship_included(self):
        """Dropship is included as a value-neutral in+out pair and still reconciles."""
        d1 = datetime(2024, 5, 5, 12, 0)
        d2 = datetime(2024, 5, 10, 12, 0)
        p = self.product_avco
        self._set_date(self._make_in_move(p, 10, unit_cost=10), d1)
        drop = self._make_dropship_move(p, 3, unit_cost=10)
        self._set_date(drop, d2)

        date_to = fields.Date.to_date('2024-05-31')
        rows = self._run(fields.Date.to_date('2024-05-01'), date_to)
        close_val, close_qty = self._closing(rows, p)
        # Dropship nets to zero on qty/value.
        self.assertAlmostEqual(close_qty, 10.0, places=2)
        self.assertAlmostEqual(close_val, 100.0, places=2)
        self.assertAlmostEqual(close_val, self._gl(p, self._frontier(date_to)), places=2)

    def test_06_standard_with_price_change(self):
        """Standard: value = qty*std; a mid-period std change emits a revaluation line
        and reconciles (D16)."""
        d1 = datetime(2024, 6, 5, 12, 0)
        d2 = datetime(2024, 6, 12, 12, 0)
        d3 = datetime(2024, 6, 20, 12, 0)
        p = self.product_standard  # standard_price 10
        self._set_date(self._make_in_move(p, 10, unit_cost=10), d1)   # 10 @ 10
        p.standard_price = 15.0                                       # creates product.value
        pv = self.env['product.value'].search(
            [('product_id', '=', p.id), ('move_id', '=', False)], order='id desc', limit=1)
        self._set_date(pv, d2)
        self._set_date(self._make_out_move(p, 4), d3)                 # 4 @ 15

        date_to = fields.Date.to_date('2024-06-30')
        rows = self._run(fields.Date.to_date('2024-06-01'), date_to)
        close_val, close_qty = self._closing(rows, p)
        self.assertAlmostEqual(close_qty, 6.0, places=2)
        self.assertAlmostEqual(close_val, 90.0, places=2)  # 6 * 15
        self.assertAlmostEqual(close_val, self._gl(p, self._frontier(date_to)), places=2)
        reval = rows.filtered(lambda r: r.line_kind == 'revaluation')
        self.assertAlmostEqual(sum(reval.mapped('in_value')), 50.0, places=2)  # (15-10)*10

    def test_07_fifo_queue(self):
        """FIFO layer queue: 10@10 + 10@20, sell 15 -> COGS 200, balance 100 == GL."""
        d1 = datetime(2024, 7, 5, 12, 0)
        d2 = datetime(2024, 7, 10, 12, 0)
        d3 = datetime(2024, 7, 20, 12, 0)
        p = self.product_fifo
        self._set_date(self._make_in_move(p, 10, unit_cost=10), d1)
        self._set_date(self._make_in_move(p, 10, unit_cost=20), d2)
        self._set_date(self._make_out_move(p, 15), d3)

        date_to = fields.Date.to_date('2024-07-31')
        rows = self._run(fields.Date.to_date('2024-07-01'), date_to)
        pr = rows.filtered(lambda r: r.product_id == p)
        close_val, close_qty = self._closing(rows, p)
        self.assertAlmostEqual(sum(pr.mapped('out_value')), 200.0, places=2)  # 10*10 + 5*20
        self.assertAlmostEqual(close_qty, 5.0, places=2)
        self.assertAlmostEqual(close_val, 100.0, places=2)  # 5 @ 20
        self.assertAlmostEqual(close_val, self._gl(p, self._frontier(date_to)), places=2)

    def test_08_fifo_negative_extrapolation(self):
        """FIFO out with no stock extrapolates the last known / standard cost."""
        d1 = datetime(2024, 8, 5, 12, 0)
        p = self.product_fifo  # standard_price 10
        self._set_date(self._make_out_move(p, 5), d1)

        date_to = fields.Date.to_date('2024-08-31')
        rows = self._run(fields.Date.to_date('2024-08-01'), date_to)
        pr = rows.filtered(lambda r: r.product_id == p)
        self.assertAlmostEqual(sum(pr.mapped('out_value')), 50.0, places=2)  # 5 * 10
        close_val, close_qty = self._closing(rows, p)
        self.assertAlmostEqual(close_qty, -5.0, places=2)
        self.assertAlmostEqual(close_val, self._gl(p, self._frontier(date_to)), places=2)

    def test_09_chaining_close_equals_next_open(self):
        """closing(month N) == opening(month N+1) (excluding method changes)."""
        # Same unit cost across months so the moving average (and standard_price) does
        # not drift: this keeps core's total_value(to_date) a faithful historical GL at
        # BOTH cutoffs, letting us assert reconciliation at each.
        d1 = datetime(2024, 9, 5, 12, 0)
        d2 = datetime(2024, 10, 8, 12, 0)
        p = self.product_avco
        self._set_date(self._make_in_move(p, 10, unit_cost=10), d1)
        self._set_date(self._make_in_move(p, 10, unit_cost=10), d2)

        sep_to = fields.Date.to_date('2024-09-30')
        oct_to = fields.Date.to_date('2024-10-31')
        rows_sep = self._run(fields.Date.to_date('2024-09-01'), sep_to)
        close_sep, close_sep_qty = self._closing(rows_sep, p)
        rows_oct = self._run(fields.Date.to_date('2024-10-01'), oct_to)
        open_oct, open_oct_qty = self._opening(rows_oct, p)
        close_oct, _q = self._closing(rows_oct, p)
        # Chaining invariant: closing of month N == opening of month N+1.
        self.assertAlmostEqual(close_sep, open_oct, places=2)
        self.assertAlmostEqual(close_sep_qty, open_oct_qty, places=2)
        self.assertAlmostEqual(close_sep, 100.0, places=2)  # 10 @ 10
        self.assertAlmostEqual(close_oct, 200.0, places=2)  # 20 @ 10
        # Both cutoffs reconcile with the GL.
        self.assertAlmostEqual(close_sep, self._gl(p, self._frontier(sep_to)), places=2)
        self.assertAlmostEqual(close_oct, self._gl(p, self._frontier(oct_to)), places=2)

    def test_10_tie_order_move_before_revaluation(self):
        """Same-date tie: the move is processed BEFORE the revaluation (source_rank)."""
        d1 = datetime(2024, 11, 10, 9, 0)
        p = self.product_avco
        self._set_date(self._make_in_move(p, 10, unit_cost=10), d1)
        pv = self.env['product.value'].create({
            'product_id': p.id, 'company_id': self.cid, 'value': 13.0})
        self._set_date(pv, d1)  # same date as the move

        date_to = fields.Date.to_date('2024-11-30')
        rows = self._run(fields.Date.to_date('2024-11-01'), date_to)
        pr = rows.filtered(lambda r: r.product_id == p).sorted(lambda r: (r.date, r.id))
        self.assertEqual(pr[0].line_kind, 'in')
        self.assertEqual(pr[1].line_kind, 'revaluation')
        close_val, _q = self._closing(rows, p)
        self.assertAlmostEqual(close_val, 130.0, places=2)  # 13 * 10
        self.assertAlmostEqual(close_val, self._gl(p, self._frontier(date_to)), places=2)

    def test_11_lot_valuated_excluded(self):
        """lot_valuated products are excluded from the scope (D4)."""
        d1 = datetime(2024, 12, 5, 12, 0)
        p = self.product_avco
        self._set_date(self._make_in_move(p, 10, unit_cost=10), d1)
        # Zero the on-hand qty before flipping lot_valuated: core stock_account
        # forbids enabling lot valuation while on-hand qty exists without a
        # lot/serial. The product stays in scope via its done valued moves.
        self._set_date(self._make_out_move(p, 10), d1)
        wiz = self.Wizard.with_context(tz='UTC').create({
            'company_id': self.cid,
            'date_from': fields.Date.to_date('2024-12-01'),
            'date_to': fields.Date.to_date('2024-12-31'),
        })
        self.assertIn(p, wiz._scope_products())
        p.product_tmpl_id.lot_valuated = True
        self.assertNotIn(p, wiz._scope_products())

    def test_12_period_validation(self):
        """date_from > date_to raises."""
        with self.assertRaises(UserError):
            self._run(fields.Date.to_date('2024-05-31'), fields.Date.to_date('2024-05-01'))

    def test_13_wipe_on_generate(self):
        """Re-running replaces (not accumulates) the user's rows (§8)."""
        d1 = datetime(2024, 5, 5, 12, 0)
        p = self.product_avco
        self._set_date(self._make_in_move(p, 10, unit_cost=10), d1)
        rows1 = self._run(fields.Date.to_date('2024-05-01'), fields.Date.to_date('2024-05-31'))
        n1 = len(rows1)
        self.assertGreater(n1, 0)
        rows2 = self._run(fields.Date.to_date('2024-05-01'), fields.Date.to_date('2024-05-31'))
        self.assertEqual(len(rows2), n1, "Re-generating must replace, not accumulate")

    def test_14_semaphore_red_refuses(self):
        """queue_max exceeded => UserError (🔴)."""
        d1 = datetime(2024, 5, 5, 12, 0)
        p = self.product_avco
        self._set_date(self._make_in_move(p, 10, unit_cost=10), d1)
        self.env['ir.config_parameter'].sudo().set_param('stock_kardex_valued.queue_max', '0')
        with self.assertRaises(UserError):
            self._run(fields.Date.to_date('2024-05-01'), fields.Date.to_date('2024-05-31'))

    def test_15_record_rule_isolates_users(self):
        """A user only sees their own generated rows (record rule §8)."""
        other = self._create_new_internal_user(
            name='Other Stock User', login='other_stock_user', groups='stock.group_stock_user')
        other.write({'company_id': self.cid, 'company_ids': [(6, 0, [self.cid])]})
        d1 = datetime(2024, 5, 5, 12, 0)
        p = self.product_avco
        self._set_date(self._make_in_move(p, 10, unit_cost=10), d1)
        rows = self._run(fields.Date.to_date('2024-05-01'), fields.Date.to_date('2024-05-31'),
                        user=self.inventory_user)
        self.assertTrue(rows)
        self.assertTrue(all(r.create_uid == self.inventory_user for r in rows))
        seen_by_other = self.KV.with_user(other).search([])
        self.assertFalse(seen_by_other, "Another user must not see these rows")

    def test_16_aggregation_flags(self):
        """*_qty/*_value aggregate with sum; bal_*/unit_cost carry no aggregator."""
        self.assertEqual(self.KV._fields['in_value'].aggregator, 'sum')
        self.assertEqual(self.KV._fields['in_qty'].aggregator, 'sum')
        self.assertFalse(self.KV._fields['bal_value'].aggregator)
        self.assertFalse(self.KV._fields['bal_unit_cost'].aggregator)
        self.assertFalse(self.KV._fields['in_unit_cost'].aggregator)
        self.assertFalse(self.KV._fields['recon_delta'].aggregator)
