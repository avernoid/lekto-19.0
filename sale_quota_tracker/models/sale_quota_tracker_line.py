# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleGoalLine(models.Model):
    _name = 'sale.goal.line'
    _description = 'Sales Goal Line'
    _order = 'goal_id, goal_type, id'

    goal_id = fields.Many2one(
        comodel_name='sale.goal',
        string='Goal',
        required=True,
        ondelete='cascade',
        index=True,
        help='Parent Sales Goal this line belongs to. Determines the salesperson, period, and data source for the achievement calculation.',
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Salesperson',
        related='goal_id.user_id',
        store=True,
        readonly=True,
        help='Salesperson from the parent goal. Inherited automatically.',
    )
    date_start = fields.Date(
        string='From',
        related='goal_id.date_start',
        store=True,
        readonly=True,
        help='Start date of the goal period. Inherited from parent goal.',
    )
    date_end = fields.Date(
        string='To',
        related='goal_id.date_end',
        store=True,
        readonly=True,
        help='End date of the goal period. Inherited from parent goal.',
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        related='goal_id.company_id',
        store=True,
        readonly=True,
        help='Company from the parent goal. Inherited automatically.',
    )
    source_type = fields.Selection(
        string='Data Source',
        related='goal_id.source_type',
        store=True,
        readonly=True,
        help='Data source for achievement calculation. Inherited from parent goal.',
    )
    period_name = fields.Char(
        string='Period',
        compute='_compute_period_name',
        store=True,
        help='Display name of the goal period (e.g., "January 2025").',
    )
    goal_type = fields.Selection(
        selection=[
            ('product', 'Product'),
            ('categ', 'Product Category'),
        ],
        string='Type',
        required=True,
        default='product',
        help='Whether the goal targets a specific product or a whole product category.',
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        help='Target product (required when Type = Product).',
    )
    categ_id = fields.Many2one(
        comodel_name='product.category',
        string='Category',
        help='Target product category (required when Type = Category).',
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='goal_id.company_id.currency_id',
        store=True,
        readonly=True,
        help='Currency used for monetary targets and achievements on this line. Inherited from the parent goal\'s company and cannot be changed directly.',
    )
    qty_goal = fields.Float(
        string='Qty Target',
        digits='Product Unit of Measure',
        help=(
            'Quantity target for this product or category in the goal period. '
            'Leave at 0 if you only want to set a revenue (amount) target. '
            'Achievement is tracked in the "Qty Achieved" field.'
        ),
    )
    amount_goal = fields.Monetary(
        string='Amount Target',
        currency_field='currency_id',
        help=(
            'Revenue target (in the company currency) for this product or category in the goal period. '
            'Leave at 0 if you only want to set a quantity target. '
            'Achievement is tracked in the "Amount Achieved" field.'
        ),
    )
    qty_done = fields.Float(
        string='Qty Achieved',
        digits='Product Unit of Measure',
        store=True,
        default=0.0,
        help=(
            'Actual quantity sold or invoiced for this product/category in the period. '
            'Updated automatically when a sale order is confirmed/cancelled or an invoice is posted/cancelled. '
            'Click "Update Results" to force a manual recalculation.'
        ),
    )
    amount_done = fields.Monetary(
        string='Amount Achieved',
        currency_field='currency_id',
        store=True,
        default=0.0,
        help=(
            'Actual revenue generated for this product/category in the period. '
            'Updated automatically when a sale order is confirmed/cancelled or an invoice is posted/cancelled. '
            'Credit notes are subtracted automatically. '
            'Click "Update Results" to force a manual recalculation.'
        ),
    )
    pct_qty = fields.Float(
        string='% Qty',
        compute='_compute_pct',
        store=True,
        digits=(6, 1),
        aggregator='avg',
        help=(
            'Percentage of the quantity target achieved (Qty Achieved / Qty Target × 100). '
            'Reaches 100% or more when the salesperson meets or exceeds the quantity goal for this line.'
        ),
    )
    pct_amount = fields.Float(
        string='% Amount',
        compute='_compute_pct',
        store=True,
        digits=(6, 1),
        aggregator='avg',
        help=(
            'Percentage of the revenue target achieved (Amount Achieved / Amount Target × 100). '
            'Reaches 100% or more when the salesperson meets or exceeds the revenue goal for this line.'
        ),
    )

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------

    @api.constrains('goal_type', 'product_id', 'categ_id')
    def _check_target_set(self):
        for line in self:
            if line.goal_type == 'product' and not line.product_id:
                raise ValidationError(_(
                    'You must select a Product when Goal Type is "Product".'
                ))
            if line.goal_type == 'categ' and not line.categ_id:
                raise ValidationError(_(
                    'You must select a Category when Goal Type is "Product Category".'
                ))

    # ------------------------------------------------------------------
    # Computed fields
    # ------------------------------------------------------------------

    @api.depends('date_start')
    def _compute_period_name(self):
        for line in self:
            if line.date_start:
                month_name = _(line.date_start.strftime('%B'))
                line.period_name = f"{month_name} {line.date_start.year}"
            else:
                line.period_name = False

    @api.depends('qty_done', 'qty_goal', 'amount_done', 'amount_goal')
    def _compute_pct(self):
        for line in self:
            line.pct_qty = (
                (line.qty_done / line.qty_goal * 100.0)
                if line.qty_goal else 0.0
            )
            line.pct_amount = (
                (line.amount_done / line.amount_goal * 100.0)
                if line.amount_goal else 0.0
            )

    # ------------------------------------------------------------------
    # Recompute logic (called by sale.goal.action_recompute and triggers)
    # ------------------------------------------------------------------

    def _compute_done(self):
        """Recalculate qty_done, amount_done, pct_qty and pct_amount for each line.

        Uses direct SQL to write results to avoid ORM cache isolation issues
        between different environment sudo contexts. Percentages are also written
        via SQL because writing qty_done/amount_done via SQL bypasses the ORM
        dependency-tracking mechanism that would normally trigger _compute_pct.
        After all SQL writes the recordset cache is invalidated for all four fields
        so subsequent ORM reads return fresh values.
        """
        ids_to_invalidate = []
        for line in self:
            goal = line.goal_id
            if not goal.date_start or not goal.date_end or not goal.user_id:
                qty, amount = 0.0, 0.0
            elif goal.source_type == 'sale_order':
                qty, amount = line._compute_from_sale_orders()
            else:
                qty, amount = line._compute_from_invoices()

            # Compute percentages here — _compute_pct won't fire because we
            # bypass the ORM with a direct SQL write.
            pct_qty = (qty / line.qty_goal * 100.0) if line.qty_goal else 0.0
            pct_amount = (amount / line.amount_goal * 100.0) if line.amount_goal else 0.0

            self.env.cr.execute(
                """UPDATE sale_goal_line\r\n                      SET qty_done = %s, amount_done = %s,
                          pct_qty  = %s, pct_amount  = %s
                    WHERE id = %s""",
                (qty, amount, pct_qty, pct_amount, line.id)
            )
            ids_to_invalidate.append(line.id)

        # Invalidate ORM cache so subsequent reads pick up the SQL-written values
        if ids_to_invalidate:
            self.browse(ids_to_invalidate).invalidate_recordset(
                ['qty_done', 'amount_done', 'pct_qty', 'pct_amount']
            )

    def _compute_from_sale_orders(self):
        """Sum qty and amount from confirmed sale.order.line records."""
        self.ensure_one()
        goal = self.goal_id
        # date_order is Datetime; use strict < first_day_of_next_month
        # so all orders on the last day of the period are included.
        date_start = goal.date_start
        date_end_exclusive = goal.date_end + timedelta(days=1)
        domain = [
            ('order_id.user_id', '=', goal.user_id.id),
            ('order_id.state', 'in', ['sale', 'done']),
            ('order_id.date_order', '>=', date_start),
            ('order_id.date_order', '<', date_end_exclusive),
            ('order_id.company_id', '=', goal.company_id.id),
        ]
        domain += self._target_domain()
        lines = self.env['sale.order.line'].sudo().search(domain)
        qty = sum(lines.mapped('product_uom_qty'))
        amount = sum(lines.mapped('price_subtotal'))
        return qty, amount

    def _compute_from_invoices(self):
        """Sum qty and amount from posted account.move.line records.

        Credit Notes (out_refund) are subtracted because they represent
        returned goods / negative revenue.
        """
        self.ensure_one()
        goal = self.goal_id
        base_domain = [
            ('move_id.invoice_user_id', '=', goal.user_id.id),
            ('move_id.move_type', 'in', ['out_invoice', 'out_refund']),
            ('move_id.state', '=', 'posted'),
            ('move_id.invoice_date', '>=', goal.date_start),
            ('move_id.invoice_date', '<=', goal.date_end),
            ('move_id.company_id', '=', goal.company_id.id),
            # No display_type filter needed: _target_domain() already
            # ensures we only match product lines via product_id.
            # (display_type varies by Odoo version: 'product' in v19, False in older)
        ]
        base_domain += self._target_domain()

        # Flush all pending ORM writes to DB before searching.
        # Required when called from inside _post() where state='posted' may
        # not yet be flushed from ORM buffer to the actual DB cursor.
        self.env.flush_all()
        move_lines = self.env['account.move.line'].sudo().search(base_domain)

        qty = 0.0
        amount = 0.0
        for ml in move_lines:
            # Credit notes represent returns — subtract them
            sign = -1.0 if ml.move_id.move_type == 'out_refund' else 1.0
            qty += sign * ml.quantity
            amount += sign * ml.price_subtotal
        return qty, amount


    def _target_domain(self):
        """Return the domain fragment filtering by product or category."""
        self.ensure_one()
        if self.goal_type == 'product':
            return [('product_id', '=', self.product_id.id)]
        else:
            return [('product_id.categ_id', 'child_of', self.categ_id.id)]
