from odoo import fields, models


class StockCostAdjustment(models.Model):
    """Cost of sales added by a late revaluation to a sale line already costed.

    Two consumers, both native:

    * ``account.move.line._get_posted_cogs_value`` (sale_stock) computes the
      cost of sales of every new invoice as *cumulative quantity x cost today
      minus what is already posted*.  Without counting these rows the next
      invoice of the same line recovers the same amount again (measured: the
      third unit went out at 650 instead of 550) -- design v4, D5.
    * A customer credit note under average cost reverses cost of sales at the
      ORIGINAL invoice price, so the share of this adjustment that belongs to
      the returned units has to be reversed alongside (D6).  ``amount`` is never
      reduced -- the cumulative formula ignores credit notes -- the reversal is
      tracked in ``reversed_amount`` instead.
    """

    _name = "stock.cost.adjustment"
    _description = "Cost of Sales Adjustment from a Late Revaluation"
    _order = "id"

    revaluation_id = fields.Many2one(
        "stock.value.revaluation", string="Revaluation", required=True,
        index=True, ondelete="cascade")
    company_id = fields.Many2one(related="revaluation_id.company_id", store=True)
    currency_id = fields.Many2one(related="revaluation_id.currency_id")
    sale_line_id = fields.Many2one(
        "sale.order.line", string="Sale Line", required=True, index=True,
        ondelete="restrict")
    amount = fields.Monetary(
        string="Cost of Sales Added", required=True,
        help="Added to the cost of sales already posted for this sale line. "
             "Counted by Odoo's cumulative cost of sales formula as already posted.")
    basis_qty = fields.Float(
        string="Units Covered", digits="Product Unit of Measure",
        help="Units whose posted cost of sales this adjustment complements. A "
             "credit note that returns some of them reverses their share.")
    reversed_amount = fields.Monetary(
        string="Reversed by Credit Notes",
        help="Part already reversed because the customer returned units.")
    account_move_id = fields.Many2one(
        related="revaluation_id.account_move_id", string="Journal Entry")
