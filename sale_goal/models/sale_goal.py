# Part of Odoo. See LICENSE file for full copyright and licensing details.

import calendar
from datetime import date, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleGoal(models.Model):
    _name = 'sale.goal'
    _description = 'Sales Goal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'year desc, month desc, user_id'
    _rec_name = 'name'

    name = fields.Char(
        string='Reference',
        compute='_compute_name',
        store=True,
        help='Auto-generated: Salesperson – Month Year',
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Salesperson',
        required=True,
        tracking=True,
        default=lambda self: self.env.user,
        help='The salesperson this goal belongs to.',
    )
    month = fields.Integer(
        string='Month',
        required=True,
        default=lambda self: fields.Date.today().month,
        help='Month number (1–12).',
    )
    year = fields.Integer(
        string='Year',
        required=True,
        default=lambda self: fields.Date.today().year,
        help='Four-digit year.',
    )
    date_start = fields.Date(
        string='From',
        compute='_compute_dates',
        store=True,
        help='First day of the goal period.',
    )
    date_end = fields.Date(
        string='To',
        compute='_compute_dates',
        store=True,
        help='Last day of the goal period.',
    )
    source_type = fields.Selection(
        selection=[
            ('sale_order', 'Confirmed Sale Orders'),
            ('invoice', 'Validated Customer Invoices'),
        ],
        string='Data Source',
        required=True,
        default='sale_order',
        tracking=True,
        help=(
            'Determines where actual qty/amount are read from:\n'
            '- Confirmed Sale Orders: uses sale.order.line\n'
            '- Validated Customer Invoices: uses account.move.line '
            '(Credit Notes are subtracted automatically)'
        ),
    )
    line_ids = fields.One2many(
        comodel_name='sale.goal.line',
        inverse_name='goal_id',
        string='Goal Lines',
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('achieved', 'Achieved'),
        ],
        string='Status',
        compute='_compute_state',
        store=True,
        help=(
            'Draft: no lines defined.\n'
            'Active: at least one line exists.\n'
            'Achieved: all lines ≥ 100% on both qty and amount.'
        ),
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='company_id.currency_id',
        store=True,
        readonly=True,
    )

    # -- Global target / achievement (header-level, no product/category filter) --
    global_amount_goal = fields.Monetary(
        string='Sales Target',
        currency_field='currency_id',
        tracking=True,
        help='Global revenue target for this period (optional). '
             'Use when you only need a single total goal without product breakdown.',
    )
    global_amount_done = fields.Monetary(
        string='Sales Achievement',
        currency_field='currency_id',
        store=True,
        default=0.0,
        readonly=True,
        help='Actual total revenue for this salesperson in the period, '
             'computed automatically from the selected Data Source.',
    )
    global_pct_amount = fields.Float(
        string='% Achievement',
        compute='_compute_global_pct',
        store=True,
        digits=(6, 1),
        help='Percentage of the global Sales Target achieved.',
    )

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------

    _unique_user_month_year = models.Constraint(
        'UNIQUE(user_id, month, year, company_id)',
        'A salesperson can only have one goal record per month and company.',
    )

    @api.constrains('month')
    def _check_month(self):
        for rec in self:
            if not 1 <= rec.month <= 12:
                raise ValidationError(_('Month must be between 1 and 12.'))

    @api.constrains('year')
    def _check_year(self):
        for rec in self:
            if rec.year < 2000 or rec.year > 2100:
                raise ValidationError(_('Year must be between 2000 and 2100.'))

    # ------------------------------------------------------------------
    # Computed fields
    # ------------------------------------------------------------------

    @api.depends('user_id', 'month', 'year')
    def _compute_name(self):
        for rec in self:
            month_name = _(date(rec.year or 2000, rec.month or 1, 1).strftime('%B'))
            rec.name = f"{rec.user_id.name or '?'} – {month_name} {rec.year or ''}"

    @api.depends('month', 'year')
    def _compute_dates(self):
        for rec in self:
            if rec.month and rec.year:
                last_day = calendar.monthrange(rec.year, rec.month)[1]
                rec.date_start = date(rec.year, rec.month, 1)
                rec.date_end = date(rec.year, rec.month, last_day)
            else:
                rec.date_start = False
                rec.date_end = False

    @api.depends('line_ids', 'line_ids.pct_qty', 'line_ids.pct_amount')
    def _compute_state(self):
        for rec in self:
            if not rec.line_ids:
                rec.state = 'draft'
            elif all(
                line.pct_qty >= 100.0 and line.pct_amount >= 100.0
                for line in rec.line_ids
            ):
                rec.state = 'achieved'
            else:
                rec.state = 'active'

    @api.depends('global_amount_done', 'global_amount_goal')
    def _compute_global_pct(self):
        for rec in self:
            rec.global_pct_amount = (
                (rec.global_amount_done / rec.global_amount_goal * 100.0)
                if rec.global_amount_goal else 0.0
            )

    # ------------------------------------------------------------------
    # Actions / Buttons
    # ------------------------------------------------------------------

    def action_recompute(self):
        """Recompute qty_done/amount_done for all lines and global achievement."""
        self.mapped('line_ids')._compute_done()
        self._recompute_global_done()
        return True

    def action_copy_previous_month(self):
        """Copy goal lines from the previous month into this goal."""
        self.ensure_one()
        prev_month = self.month - 1 if self.month > 1 else 12
        prev_year = self.year if self.month > 1 else self.year - 1
        prev_goal = self.search([
            ('user_id', '=', self.user_id.id),
            ('month', '=', prev_month),
            ('year', '=', prev_year),
            ('company_id', '=', self.company_id.id),
        ], limit=1)
        if not prev_goal:
            raise ValidationError(_(
                'No goal found for %(name)s in %(month)s %(year)s.',
                name=self.user_id.name,
                month=prev_month,
                year=prev_year,
            ))
        for line in prev_goal.line_ids:
            self.env['sale.goal.line'].create({
                'goal_id': self.id,
                'goal_type': line.goal_type,
                'product_id': line.product_id.id if line.product_id else False,
                'categ_id': line.categ_id.id if line.categ_id else False,
                'qty_goal': line.qty_goal,
                'amount_goal': line.amount_goal,
            })
        # Also copy the global Sales Target from the previous month
        if prev_goal.global_amount_goal:
            self.global_amount_goal = prev_goal.global_amount_goal
        return True

    # ------------------------------------------------------------------
    # Global recompute (no product/category filter)
    # ------------------------------------------------------------------

    def _recompute_global_done(self):
        """Recompute global_amount_done and global_pct_amount for each goal.

        Sums ALL revenue for the salesperson in the period from the configured
        source (sale orders or invoices), without any product/category filter.
        Written via SQL (same pattern as SaleGoalLine._compute_done) to avoid
        ORM cache isolation issues and to refresh the stored computed field.
        """
        for goal in self:
            if not goal.date_start or not goal.date_end or not goal.user_id:
                amount = 0.0
            elif goal.source_type == 'sale_order':
                amount = goal._global_amount_from_sale_orders()
            else:
                amount = goal._global_amount_from_invoices()

            pct = (amount / goal.global_amount_goal * 100.0) if goal.global_amount_goal else 0.0
            self.env.cr.execute(
                """UPDATE sale_goal
                      SET global_amount_done = %s, global_pct_amount = %s
                    WHERE id = %s""",
                (amount, pct, goal.id)
            )
        self.invalidate_recordset(['global_amount_done', 'global_pct_amount'])

    def _global_amount_from_sale_orders(self):
        """Sum price_subtotal from confirmed sale.order.line for this goal period."""
        self.ensure_one()
        date_end_exclusive = self.date_end + timedelta(days=1)
        lines = self.env['sale.order.line'].sudo().search([
            ('order_id.user_id', '=', self.user_id.id),
            ('order_id.state', 'in', ['sale', 'done']),
            ('order_id.date_order', '>=', self.date_start),
            ('order_id.date_order', '<', date_end_exclusive),
            ('order_id.company_id', '=', self.company_id.id),
        ])
        return sum(lines.mapped('price_subtotal'))

    def _global_amount_from_invoices(self):
        """Sum price_subtotal from posted account.move.line for this goal period.

        Credit notes are subtracted (negative revenue).
        """
        self.ensure_one()
        self.env.flush_all()
        move_lines = self.env['account.move.line'].sudo().search([
            ('move_id.invoice_user_id', '=', self.user_id.id),
            ('move_id.move_type', 'in', ['out_invoice', 'out_refund']),
            ('move_id.state', '=', 'posted'),
            ('move_id.invoice_date', '>=', self.date_start),
            ('move_id.invoice_date', '<=', self.date_end),
            ('move_id.company_id', '=', self.company_id.id),
            ('product_id', '!=', False),
        ])
        amount = 0.0
        for ml in move_lines:
            sign = -1.0 if ml.move_id.move_type == 'out_refund' else 1.0
            amount += sign * ml.price_subtotal
        return amount
