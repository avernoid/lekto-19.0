from odoo import api, fields, models


class StockValueVariance(models.Model):
    """One dated amount per stock movement, left by a late revaluation.

    Since 19.0.2.0.0 a row no longer carries a correction to be applied later:
    the correction is written into the movement's stored ``value`` by the
    revaluation engine (``stock.value.revaluation``), and the row is the record
    of *what* was folded, *when* and *why*.  That record is what lets a report
    rebuild the value of a past date as it was known then (design v4, D7).

    Rows that are not folded (``absorbed = False``) are the ones the stored
    value cannot carry -- the value the native AVCO replay drops when an entry
    lands on negative stock, or a FIFO lot valued apart from its exits (D9) -- and
    they are added on top by every ledger.
    """

    _name = "stock.value.variance"
    _description = "Stock Value Variance"
    _order = "date desc, id desc"

    move_id = fields.Many2one(
        "stock.move", string="Stock Move", required=True,
        index=True, ondelete="cascade",
        help="The stock movement whose value the revaluation changed.")
    product_id = fields.Many2one(
        "product.product", related="move_id.product_id", store=True, index=True)
    company_id = fields.Many2one(
        "res.company", string="Company", required=True, index=True)
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id")
    revaluation_id = fields.Many2one(
        "stock.value.revaluation", string="Revaluation", index=True,
        ondelete="cascade",
        help="The late revaluation event that produced this amount.")

    kind = fields.Selection(
        [("exit", "Exit restated"),
         ("return", "Return re-derived"),
         ("entry", "Entry revalued by a bill"),
         ("negative_stock", "Value dropped by the engine"),
         ("recalc", "Historical rebuild"),
         ("legacy", "Legacy (19.0.1)")],
        string="Kind", required=True, default="exit", index=True,
        help="Exit restated: an outgoing movement rewritten to the cost Odoo's "
             "engine gives it today. Return re-derived: a customer return "
             "re-valued from its restated delivery. Entry revalued by a bill: the "
             "part of a vendor bill that changed a receipt already done. Value dropped "
             "by the engine: value Odoo's inventory value does not keep from the "
             "movements -- goods arriving on negative stock, or a FIFO lot whose "
             "exits took the average of its entries; no movement carries it, so it "
             "is added on top. Historical rebuild: written by the valuation rebuild wizard. "
             "Legacy: rows of version 19.0.1, kept for the record and ignored.")
    origin = fields.Selection(
        [("landed_cost", "Landed Cost"),
         ("bill", "Vendor Bill"),
         ("recalc", "Valuation Recalculation")],
        string="Legacy Origin",
        help="Origin recorded by version 19.0.1. Not used by the engine.")

    date = fields.Datetime(
        string="Date", required=True,
        help="Date of the event that produced the amount, not the movement's "
             "own date. Reports use it to rebuild a past date as it was known.")
    ledger_amount = fields.Monetary(
        string="Ledger Effect", required=True,
        help="Signed amount this row represents in a valued ledger: positive "
             "raises the stock value, negative lowers it.")
    absorbed = fields.Boolean(
        string="Folded into Value", default=True, index=True,
        help="Checked when the amount is already written into the movement's "
             "stored value. Unchecked rows are added on top by every ledger.")

    valued_qty = fields.Float(
        string="Valued Qty", digits="Product Unit of Measure",
        help="Quantity valued by the movement, in the product's unit.")
    remaining_qty = fields.Float(
        string="Remaining Qty", digits="Product Unit of Measure",
        help="Legacy (19.0.1): quantity still in stock at the revaluation.")

    # Legacy columns of 19.0.1, kept read-only so no history is lost.
    landed_cost_line_id = fields.Many2one(
        "stock.valuation.adjustment.lines", string="Landed Cost Line",
        ondelete="set null", index="btree_not_null", readonly=True)
    account_move_id = fields.Many2one(
        "account.move", string="Source Bill", index="btree_not_null", readonly=True)
    base_amount = fields.Monetary(string="Legacy Revaluation", readonly=True)
    capitalized_amount = fields.Monetary(string="Legacy Capitalised", readonly=True)
    expensed_amount = fields.Monetary(string="Legacy Belongs to Goods Gone", readonly=True)
    variance_move_id = fields.Many2one(
        "account.move", string="Legacy Reclassification Entry",
        readonly=True, copy=False, index="btree_not_null",
        help="Reclassification entry posted by version 19.0.1. Kept, never "
             "reversed automatically: review it with the revaluation events.")

    # ------------------------------------------------------------------
    def _ledger_signed_amount(self):
        """What this row adds on top of the stored value in a valued ledger."""
        self.ensure_one()
        return 0.0 if self.absorbed else self.ledger_amount

    @api.model
    def _variance_live_rows(self, moves, date_to=None):
        """Rows not folded into the value, optionally only those known at ``date_to``."""
        domain = [("move_id", "in", moves.ids), ("absorbed", "=", False),
                  ("kind", "!=", "legacy")]
        if date_to:
            domain.append(("date", "<=", date_to))
        return self.sudo().search(domain)
