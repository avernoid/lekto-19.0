# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
import calendar

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSaleGoalCompute(TransactionCase):
    """Tests for the _compute_done logic on sale.goal.line.

    Covers both source_type modes (sale_order / invoice), product and
    category goals, period boundaries, and Credit Note sign handling.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env.company

        # ── Category hierarchy ───────────────────────────────────────────
        cls.categ_parent = cls.env['product.category'].create({
            'name': 'Test Electronics',
        })
        cls.categ_child = cls.env['product.category'].create({
            'name': 'Test Laptops',
            'parent_id': cls.categ_parent.id,
        })

        # ── Products ─────────────────────────────────────────────────────
        cls.product_a = cls.env['product.product'].create({
            'name': 'Laptop Pro',
            'type': 'consu',
            'categ_id': cls.categ_child.id,
            'list_price': 1000.0,
        })
        cls.product_b = cls.env['product.product'].create({
            'name': 'Mouse',
            'type': 'consu',
            'categ_id': cls.categ_child.id,
            'list_price': 50.0,
        })

        # ── Salesperson users ─────────────────────────────────────────────
        group_sales = cls.env.ref('sales_team.group_sale_salesman')
        cls.salesperson = cls.env['res.users'].create({
            'name': 'Test Vendor',
            'login': 'test_vendor_goal',
            'group_ids': [(6, 0, [group_sales.id])],
        })
        cls.other_salesperson = cls.env['res.users'].create({
            'name': 'Other Vendor',
            'login': 'other_vendor_goal',
            'group_ids': [(6, 0, [group_sales.id])],
        })

        # ── Partners ──────────────────────────────────────────────────────
        cls.partner = cls.env['res.partner'].create({'name': 'Test Customer'})

        # ── Current period (this month) ───────────────────────────────────
        today = date.today()
        cls.current_month = today.month
        cls.current_year = today.year

        # ── Accounting setup for invoice tests ────────────────────────────
        # Find a free account code to avoid Unique Violation on dirty DBs
        income_code = 700000
        while cls.env['account.account'].search(
            [('code', '=', str(income_code)),
             ('company_ids', 'in', cls.company.id)], limit=1
        ):
            income_code += 1

        cls.income_account = cls.env['account.account'].create({
            'name': 'Test Income Goal',
            'code': str(income_code),
            'account_type': 'income',
            'company_ids': [(4, cls.company.id)],
        })

        cls.sale_journal = cls.env['account.journal'].create({
            'name': 'Test Sales Journal Goal',
            'type': 'sale',
            'default_account_id': cls.income_account.id,
            'company_id': cls.company.id,
        })

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _make_goal(self, source_type='sale_order', user=None):
        """Create a sale.goal for the current month."""
        return self.env['sale.goal'].create({
            'user_id': (user or self.salesperson).id,
            'month': self.current_month,
            'year': self.current_year,
            'source_type': source_type,
            'company_id': self.company.id,
        })

    def _make_goal_line(self, goal, goal_type='product', product=None, categ=None,
                        qty_goal=10.0, amount_goal=5000.0):
        return self.env['sale.goal.line'].create({
            'goal_id': goal.id,
            'goal_type': goal_type,
            'product_id': (product or (self.product_a if goal_type == 'product' else False)).id
                          if goal_type == 'product' else False,
            'categ_id': (categ or self.categ_parent).id if goal_type == 'categ' else False,
            'qty_goal': qty_goal,
            'amount_goal': amount_goal,
        })

    def _make_confirmed_so(self, user, product, qty=1.0, price=1000.0,
                           order_date=None):
        """Create and confirm a Sale Order in the current month."""
        if order_date is None:
            order_date = date(self.current_year, self.current_month, 15)
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'user_id': user.id,
            'date_order': order_date,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': qty,
                'price_unit': price,
            })],
        })
        so.action_confirm()
        return so

    def _make_posted_invoice(self, user, product, qty=1.0, price=1000.0,
                             move_type='out_invoice', inv_date=None):
        """Create and post a customer invoice."""
        if inv_date is None:
            # Use today to avoid Odoo 19's future-date auto_post deferral.
            # Tests that need specific period dates pass inv_date explicitly.
            inv_date = date.today()
        move = self.env['account.move'].create({
            'move_type': move_type,
            'partner_id': self.partner.id,
            'invoice_user_id': user.id,
            'invoice_date': inv_date,
            'journal_id': self.sale_journal.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id,
                'quantity': qty,
                'price_unit': price,
                'account_id': self.income_account.id,
            })],
        })
        # soft=False forces immediate posting regardless of date.
        # soft=True (default) defers future-dated invoices to auto_post silently.
        move._post(soft=False)
        return move


    # ── Tests: Sale Order source ──────────────────────────────────────────

    def test_compute_from_sale_order_product(self):
        """A confirmed SO with the exact product increments qty_done and amount_done."""
        goal = self._make_goal(source_type='sale_order')
        line = self._make_goal_line(goal, goal_type='product', product=self.product_a,
                                    qty_goal=10.0, amount_goal=5000.0)

        self._make_confirmed_so(self.salesperson, self.product_a, qty=3.0, price=1000.0)

        line._compute_done()

        self.assertAlmostEqual(line.qty_done, 3.0, places=2,
                               msg='qty_done must equal the SO line qty')
        self.assertAlmostEqual(line.amount_done, 3000.0, places=2,
                               msg='amount_done must equal price_subtotal from SO line')

    def test_compute_from_sale_order_category_child_of(self):
        """A goal by parent category must include products in child categories."""
        goal = self._make_goal(source_type='sale_order')
        # categ_parent contains categ_child, which contains product_a
        line = self._make_goal_line(goal, goal_type='categ', categ=self.categ_parent)

        self._make_confirmed_so(self.salesperson, self.product_a, qty=5.0, price=1000.0)

        line._compute_done()

        self.assertAlmostEqual(line.qty_done, 5.0, places=2,
                               msg='child_of domain must include products in subcategories')

    def test_compute_excludes_draft_sale_orders(self):
        """Draft (unconfirmed) sale orders must NOT count towards the goal."""
        goal = self._make_goal(source_type='sale_order')
        line = self._make_goal_line(goal, goal_type='product', product=self.product_a)

        # Create a draft SO but do NOT confirm it
        self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'user_id': self.salesperson.id,
            'date_order': date(self.current_year, self.current_month, 15),
            'order_line': [(0, 0, {
                'product_id': self.product_a.id,
                'product_uom_qty': 5.0,
                'price_unit': 1000.0,
            })],
        })
        line._compute_done()

        self.assertAlmostEqual(line.qty_done, 0.0, places=2,
                               msg='Draft SOs must not contribute to the goal')

    def test_compute_excludes_other_salesperson_orders(self):
        """SOs from a different salesperson must not count for this goal."""
        goal = self._make_goal(source_type='sale_order')
        line = self._make_goal_line(goal, goal_type='product', product=self.product_a)

        # Confirm an SO for a DIFFERENT salesperson
        self._make_confirmed_so(self.other_salesperson, self.product_a, qty=7.0, price=1000.0)

        line._compute_done()

        self.assertAlmostEqual(line.qty_done, 0.0, places=2,
                               msg='Other salesperson orders must not count')

    def test_compute_excludes_out_of_period_orders(self):
        """SO confirmed outside the goal period must not be counted."""
        goal = self._make_goal(source_type='sale_order')
        line = self._make_goal_line(goal, goal_type='product', product=self.product_a)

        # Date in previous month
        prev_month = self.current_month - 1 if self.current_month > 1 else 12
        prev_year = self.current_year if self.current_month > 1 else self.current_year - 1
        prev_date = date(prev_year, prev_month, 15)

        so = self._make_confirmed_so(self.salesperson, self.product_a, qty=4.0,
                                 price=1000.0, order_date=prev_date)
        # NOTE: Odoo 19's action_confirm() rewrites date_order to now().
        # We force it back to the previous month to test the period filter.
        so.sudo().write({'date_order': prev_date})

        line._compute_done()

        self.assertAlmostEqual(line.qty_done, 0.0, places=2,
                               msg='SOs outside the month period must not count')

    # ── Tests: Invoice source ─────────────────────────────────────────────

    def test_compute_from_invoice_product(self):
        """A posted invoice increments qty_done and amount_done correctly."""
        goal = self._make_goal(source_type='invoice')
        line = self._make_goal_line(goal, goal_type='product', product=self.product_a,
                                    qty_goal=10.0, amount_goal=5000.0)

        self._make_posted_invoice(self.salesperson, self.product_a, qty=4.0, price=1000.0)

        line._compute_done()

        self.assertAlmostEqual(line.qty_done, 4.0, places=2)
        self.assertAlmostEqual(line.amount_done, 4000.0, places=2)

    def test_compute_credit_note_subtracts(self):
        """A credit note (out_refund) must SUBTRACT from qty_done and amount_done."""
        goal = self._make_goal(source_type='invoice')
        line = self._make_goal_line(goal, goal_type='product', product=self.product_a,
                                    qty_goal=10.0, amount_goal=5000.0)

        # Invoice: +10 units
        self._make_posted_invoice(self.salesperson, self.product_a, qty=10.0, price=500.0)
        # Credit Note: -3 units
        self._make_posted_invoice(self.salesperson, self.product_a, qty=3.0, price=500.0,
                                  move_type='out_refund')

        line._compute_done()

        self.assertAlmostEqual(line.qty_done, 7.0, places=2,
                               msg='Credit note must subtract from qty_done')
        self.assertAlmostEqual(line.amount_done, 3500.0, places=2,
                               msg='Credit note must subtract from amount_done')

    def test_compute_excludes_draft_invoices(self):
        """Draft (unposted) invoices must not count towards the goal."""
        goal = self._make_goal(source_type='invoice')
        line = self._make_goal_line(goal, goal_type='product', product=self.product_a)

        # Create but do NOT post the invoice
        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'invoice_user_id': self.salesperson.id,
            'invoice_date': date(self.current_year, self.current_month, 15),
            'journal_id': self.sale_journal.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'quantity': 5.0,
                'price_unit': 1000.0,
                'account_id': self.income_account.id,
            })],
        })
        line._compute_done()

        self.assertAlmostEqual(line.qty_done, 0.0, places=2,
                               msg='Draft invoices must not count')

    # ── Tests: Percentage computation ─────────────────────────────────────

    def test_pct_amount_full_achievement(self):
        """pct_amount must be 100% when amount_done equals amount_goal."""
        goal = self._make_goal(source_type='sale_order')
        line = self._make_goal_line(goal, qty_goal=5.0, amount_goal=1000.0)

        self._make_confirmed_so(self.salesperson, self.product_a, qty=5.0, price=200.0)
        line._compute_done()

        self.assertAlmostEqual(line.pct_amount, 100.0, delta=1.0,
                               msg='pct_amount must be 100% when target is met')

    def test_pct_zero_when_goal_is_zero(self):
        """pct_qty and pct_amount must be 0.0 when goal values are 0 (avoid division by zero)."""
        goal = self._make_goal(source_type='sale_order')
        line = self._make_goal_line(goal, qty_goal=0.0, amount_goal=0.0)

        line._compute_done()

        self.assertAlmostEqual(line.pct_qty, 0.0, places=2)
        self.assertAlmostEqual(line.pct_amount, 0.0, places=2)

    # ── Tests: Constraints ────────────────────────────────────────────────

    def test_unique_constraint_same_user_month_year(self):
        """Creating two goals for the same user/month/year must raise an error."""
        from odoo.exceptions import ValidationError
        from psycopg2 import IntegrityError
        from odoo.tools import mute_logger

        self._make_goal(source_type='sale_order')

        raised = False
        try:
            with mute_logger('odoo.sql_db'):
                self.env['sale.goal'].create({
                    'user_id': self.salesperson.id,
                    'month': self.current_month,
                    'year': self.current_year,
                    'source_type': 'invoice',
                    'company_id': self.company.id,
                })
        except (ValidationError, IntegrityError):
            raised = True
        self.assertTrue(raised, 'Expected ValidationError or IntegrityError for duplicate goal')

    def test_goal_line_requires_product_when_type_product(self):
        """Creating a goal line with goal_type='product' and no product_id must fail."""
        from odoo.exceptions import ValidationError
        goal = self._make_goal()
        with self.assertRaises(ValidationError):
            self.env['sale.goal.line'].create({
                'goal_id': goal.id,
                'goal_type': 'product',
                # product_id intentionally omitted
                'qty_goal': 10.0,
                'amount_goal': 1000.0,
            })

    def test_goal_line_requires_categ_when_type_categ(self):
        """Creating a goal line with goal_type='categ' and no categ_id must fail."""
        from odoo.exceptions import ValidationError
        goal = self._make_goal()
        with self.assertRaises(ValidationError):
            self.env['sale.goal.line'].create({
                'goal_id': goal.id,
                'goal_type': 'categ',
                # categ_id intentionally omitted
                'qty_goal': 10.0,
                'amount_goal': 1000.0,
            })


@tagged('post_install', '-at_install')
class TestSaleGoalTriggers(TransactionCase):
    """Tests for automatic recompute triggers on sale.order and account.move."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.categ = cls.env['product.category'].create({
            'name': 'Trigger Category',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Trigger Product',
            'type': 'consu',
            'categ_id': cls.categ.id,
            'list_price': 500.0,
        })
        cls.partner = cls.env['res.partner'].create({'name': 'Trigger Partner'})

        group_sales = cls.env.ref('sales_team.group_sale_salesman')
        cls.salesperson = cls.env['res.users'].create({
            'name': 'Trigger Vendor',
            'login': 'trigger_vendor_goal',
            'group_ids': [(6, 0, [group_sales.id])],
        })

        today = date.today()
        cls.current_month = today.month
        cls.current_year = today.year

        # Accounting setup
        income_code = 710000
        while cls.env['account.account'].search(
            [('code', '=', str(income_code)),
             ('company_ids', 'in', cls.company.id)], limit=1
        ):
            income_code += 1

        cls.income_account = cls.env['account.account'].create({
            'name': 'Trigger Income',
            'code': str(income_code),
            'account_type': 'income',
            'company_ids': [(4, cls.company.id)],
        })
        cls.sale_journal = cls.env['account.journal'].create({
            'name': 'Trigger Sales Journal',
            'type': 'sale',
            'default_account_id': cls.income_account.id,
            'company_id': cls.company.id,
        })

    def _make_goal_with_line(self, source_type='sale_order'):
        goal = self.env['sale.goal'].create({
            'user_id': self.salesperson.id,
            'month': self.current_month,
            'year': self.current_year,
            'source_type': source_type,
            'company_id': self.company.id,
        })
        line = self.env['sale.goal.line'].create({
            'goal_id': goal.id,
            'goal_type': 'product',
            'product_id': self.product.id,
            'qty_goal': 20.0,
            'amount_goal': 10000.0,
        })
        return goal, line

    def test_trigger_on_so_confirm_updates_goal(self):
        """Confirming a SO automatically recomputes sale_order goals."""
        _goal, line = self._make_goal_with_line(source_type='sale_order')

        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'user_id': self.salesperson.id,
            'date_order': date(self.current_year, self.current_month, 10),
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 5.0,
                'price_unit': 500.0,
            })],
        })
        self.assertAlmostEqual(line.qty_done, 0.0, places=2,
                               msg='Before confirm qty_done must be 0')
        so.action_confirm()

        self.assertAlmostEqual(line.qty_done, 5.0, places=2,
                               msg='After SO confirm qty_done must update automatically')

    def test_trigger_on_so_cancel_updates_goal(self):
        """Cancelling a confirmed SO decrements the goal."""
        _goal, line = self._make_goal_with_line(source_type='sale_order')

        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'user_id': self.salesperson.id,
            'date_order': date(self.current_year, self.current_month, 10),
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 6.0,
                'price_unit': 500.0,
            })],
        })
        so.action_confirm()
        self.assertAlmostEqual(line.qty_done, 6.0, places=2)

        so.action_cancel()
        self.assertAlmostEqual(line.qty_done, 0.0, places=2,
                               msg='After SO cancel qty_done must be 0')

    def test_trigger_on_invoice_post_updates_goal(self):
        """Posting an invoice automatically recomputes invoice goals."""
        _goal, line = self._make_goal_with_line(source_type='invoice')

        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'invoice_user_id': self.salesperson.id,
            'invoice_date': date.today(),
            'journal_id': self.sale_journal.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 8.0,
                'price_unit': 500.0,
                'account_id': self.income_account.id,
            })],
        })
        self.assertAlmostEqual(line.qty_done, 0.0, places=2,
                               msg='Before posting qty_done must be 0')
        move._post(soft=False)

        self.assertAlmostEqual(line.qty_done, 8.0, places=2,
                               msg='After invoice post qty_done must update automatically')

    def test_no_cross_source_trigger(self):
        """Confirming an SO must NOT affect an invoice-source goal and vice versa."""
        _goal_so, line_so = self._make_goal_with_line(source_type='sale_order')

        # Create a second goal (different instance needed since unique constraint)
        # Use other_salesperson to avoid UNIQUE violation
        group_sales = self.env.ref('sales_team.group_sale_salesman')
        other_user = self.env['res.users'].create({
            'name': 'Other Trigger Vendor',
            'login': 'other_trigger_vendor',
            'group_ids': [(6, 0, [group_sales.id])],
        })
        goal_inv = self.env['sale.goal'].create({
            'user_id': other_user.id,
            'month': self.current_month,
            'year': self.current_year,
            'source_type': 'invoice',
            'company_id': self.company.id,
        })
        line_inv = self.env['sale.goal.line'].create({
            'goal_id': goal_inv.id,
            'goal_type': 'product',
            'product_id': self.product.id,
            'qty_goal': 20.0,
            'amount_goal': 10000.0,
        })

        # Confirm SO for salesperson → only affects sale_order goals for salesperson
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'user_id': self.salesperson.id,
            'date_order': date(self.current_year, self.current_month, 10),
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 5.0,
                'price_unit': 500.0,
            })],
        })
        so.action_confirm()

        self.assertAlmostEqual(line_so.qty_done, 5.0, places=2,
                               msg='SO-source goal for salesperson must update')
        self.assertAlmostEqual(line_inv.qty_done, 0.0, places=2,
                               msg='Invoice-source goal must NOT be triggered by SO confirm')


@tagged('post_install', '-at_install')
class TestSaleGoalSecurity(TransactionCase):
    """Tests for Record Rules: salesperson can only read own goals."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        today = date.today()
        cls.current_month = today.month
        cls.current_year = today.year

        group_sales = cls.env.ref('sales_team.group_sale_salesman')
        group_manager = cls.env.ref('sales_team.group_sale_manager')

        cls.manager = cls.env['res.users'].create({
            'name': 'Goal Manager',
            'login': 'goal_manager_user',
            'group_ids': [(6, 0, [group_manager.id])],
        })
        cls.vendor_a = cls.env['res.users'].create({
            'name': 'Vendor A',
            'login': 'vendor_a_goal',
            'group_ids': [(6, 0, [group_sales.id])],
        })
        cls.vendor_b = cls.env['res.users'].create({
            'name': 'Vendor B',
            'login': 'vendor_b_goal',
            'group_ids': [(6, 0, [group_sales.id])],
        })

        # Create goals for both vendors (different months to avoid UNIQUE collision)
        cls.goal_a = cls.env['sale.goal'].create({
            'user_id': cls.vendor_a.id,
            'month': cls.current_month,
            'year': cls.current_year,
            'source_type': 'sale_order',
            'company_id': cls.company.id,
        })
        # Use a different month for vendor_b to avoid UNIQUE violation
        alt_month = cls.current_month % 12 + 1
        alt_year = cls.current_year if alt_month != 1 else cls.current_year + 1
        cls.goal_b = cls.env['sale.goal'].create({
            'user_id': cls.vendor_b.id,
            'month': alt_month,
            'year': alt_year,
            'source_type': 'sale_order',
            'company_id': cls.company.id,
        })

    def test_salesperson_sees_only_own_goals(self):
        """Vendor A must not see Vendor B's goal via search."""
        goals_as_vendor_a = self.env['sale.goal'].with_user(self.vendor_a).search([])
        goal_ids = goals_as_vendor_a.ids
        self.assertIn(self.goal_a.id, goal_ids,
                      'Vendor A must see their own goal')
        self.assertNotIn(self.goal_b.id, goal_ids,
                         'Vendor A must NOT see Vendor B goal')

    def test_manager_sees_all_goals(self):
        """Sales Manager must see goals for all salespeople."""
        goals_as_manager = self.env['sale.goal'].with_user(self.manager).search([])
        goal_ids = goals_as_manager.ids
        self.assertIn(self.goal_a.id, goal_ids,
                      'Manager must see Vendor A goal')
        self.assertIn(self.goal_b.id, goal_ids,
                      'Manager must see Vendor B goal')

    def test_salesperson_cannot_write_own_goal(self):
        """Salesperson must not be allowed to write/modify their own goal."""
        from odoo.exceptions import AccessError
        with self.assertRaises(AccessError):
            self.env['sale.goal'].with_user(self.vendor_a).browse(
                self.goal_a.id
            ).write({'source_type': 'invoice'})
