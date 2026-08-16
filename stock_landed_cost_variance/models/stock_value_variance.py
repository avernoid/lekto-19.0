from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class StockValueVariance(models.Model):
    """One row per (movement, revaluation event).

    Deliberately a model of its own rather than fields on
    ``stock.valuation.adjustment.lines``: that model requires ``cost_id``, is
    only ever created by ``compute_landed_cost`` -- which is public, has no
    state guard and starts by unlinking every line of the cost -- and any row
    living there is summed into ``move.value`` by
    ``stock_landed_costs``'s ``_get_value_from_extra``.  A marker kept there
    would disarm itself and a synthetic row would double-count in the ledger.
    """

    _name = "stock.value.variance"
    _description = "Stock Value Variance"
    _inherit = ["mail.thread"]
    _order = "date desc, id desc"

    move_id = fields.Many2one(
        "stock.move", string="Stock Move", required=True,
        index=True, ondelete="cascade",
        help="The stock movement whose value was changed after it was done. "
             "The row is deleted with it.")
    product_id = fields.Many2one(
        "product.product", related="move_id.product_id", store=True, index=True)
    company_id = fields.Many2one(
        "res.company", string="Company", required=True, index=True,
        help="Company the revaluation belongs to. It decides the accounts used "
             "and groups the reclassification entry: one entry per company.")
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id")

    origin = fields.Selection(
        [("landed_cost", "Landed Cost"),
         ("bill", "Vendor Bill"),
         ("recalc", "Valuation Recalculation")],
        string="Origin", required=True, index=True,
        help="What revalued the movement, which decides how it is accounted "
             "for. Landed Cost: the amount stayed in the freight expense "
             "account and is taken through inventory to cost of sales. Vendor "
             "Bill: the bill already moved the valuation account, so the "
             "amount only has to come out of it -- and under periodic "
             "valuation no entry is needed at all, because the closing already "
             "gets it right. Valuation Recalculation: bookkeeping of a "
             "recalculation, never posted.")
    landed_cost_line_id = fields.Many2one(
        "stock.valuation.adjustment.lines", string="Landed Cost Line",
        ondelete="set null", index="btree_not_null",
        help="The landed cost line that revalued the movement. Kept as "
             "evidence; the row survives if the line disappears.")
    account_move_id = fields.Many2one(
        "account.move", string="Source Bill", index="btree_not_null",
        help="The vendor bill whose posting revalued the movement.")

    date = fields.Datetime(
        string="Date", required=True,
        help="Date of the event that revalued the movement, not the movement's own date.")

    base_amount = fields.Monetary(
        string="Revaluation", required=True,
        help="Whole amount by which the movement was revalued. It always "
             "equals Capitalised plus Belongs to Goods Gone.")
    capitalized_amount = fields.Monetary(
        string="Capitalised", required=True,
        help="Part of the revaluation that landed on goods still in stock.")
    expensed_amount = fields.Monetary(
        string="Belongs to Goods Gone", required=True, tracking=True,
        groups="account.group_account_manager",
        help="Part of the revaluation attributable to goods that had already "
             "left when the revaluation happened.")
    valued_qty = fields.Float(
        string="Valued Qty", digits="Product Unit of Measure",
        help="Quantity valued by the movement, in the product's unit.")
    remaining_qty = fields.Float(
        string="Remaining Qty", digits="Product Unit of Measure",
        help="Quantity still in stock when the revaluation happened, in the "
             "product's unit.")
    lot_id = fields.Many2one(
        "stock.lot", string="Lot/Serial",
        help="Set on lot-valuated products, where the revaluation is split "
             "into one row per lot. Empty otherwise.")

    ledger_amount = fields.Monetary(
        string="Ledger Effect", required=True,
        help="Signed amount this row adds to a valued ledger. Stored rather "
             "than derived so every consumer reads one number and no consumer "
             "has to know the sign rules of each origin.")

    absorbed = fields.Boolean(
        string="Absorbed", default=False, tracking=True,
        help="A valuation recalculation has already folded this variance into "
             "the movement values, so it must no longer be applied on top.")
    variance_move_id = fields.Many2one(
        "account.move", string="Reclassification Entry",
        readonly=True, copy=False, index="btree_not_null",
        help="The journal entry that recognised this variance as cost of "
             "sales. Set once and never cleared: it is what stops the same "
             "amount from being posted twice. While it is posted the split "
             "cannot be edited -- reverse the entry first.")

    # ------------------------------------------------------------------
    @api.constrains("base_amount", "capitalized_amount", "expensed_amount")
    def _check_split(self):
        for variance in self:
            currency = variance.currency_id or variance.company_id.currency_id
            residual = variance.base_amount - variance.capitalized_amount - variance.expensed_amount
            if not currency.is_zero(residual):
                raise UserError(_(
                    "The capitalised and expensed parts must add up to the "
                    "revaluation (%(base)s != %(cap)s + %(exp)s).",
                    base=variance.base_amount,
                    cap=variance.capitalized_amount,
                    exp=variance.expensed_amount,
                ))

    def write(self, vals):
        if "expensed_amount" in vals:
            posted = self.filtered(
                lambda v: v.variance_move_id.state == "posted")
            if posted:
                raise UserError(_(
                    "This variance is already backed by a posted entry (%s). "
                    "Reset or reverse that entry before changing the amount.",
                    ", ".join(posted.mapped("variance_move_id.name")),
                ))
            # Paired write: the split must keep adding up to base_amount, and
            # the ledger effect must keep matching the expensed part.
            for variance in self:
                vals_line = dict(vals)
                vals_line["capitalized_amount"] = (
                    variance.base_amount - vals["expensed_amount"])
                if "ledger_amount" not in vals:
                    # Only derive it when the caller has not stated it: a
                    # recalculation writes its own sign, which is not the one a
                    # revaluation would carry on the same move.
                    vals_line["ledger_amount"] = self._ledger_amount_for(
                        variance.move_id, vals["expensed_amount"])
                super(StockValueVariance, variance).write(vals_line)
            return True
        return super().write(vals)

    # ------------------------------------------------------------------
    def action_post_reclassification(self):
        """Post ONE aggregated entry for the selected variances.

        Deliberately an explicit action rather than a hook inside
        ``button_validate`` / ``_post``: raising there because the period is
        locked would make it impossible to validate the landed cost or post the
        bill at all.

        The variance rows are the entry's supporting schedule -- the sum is the
        amount and each row is a line of the working paper -- so the link is
        kept in both directions.
        """
        candidates = self._reclassification_candidates()
        if not candidates:
            raise UserError(_("Nothing to reclassify in the selection."))

        # No boolean-read-then-write: two concurrent sweeps would both post.
        self.env.cr.execute(
            "SELECT id FROM stock_value_variance WHERE id IN %s FOR UPDATE",
            (tuple(candidates.ids),))

        moves = self.env["account.move"]
        for company, per_company in candidates.grouped("company_id").items():
            moves |= per_company.with_company(company)._post_company_reclassification()
        return moves

    def _reclassification_candidates(self):
        """Rows that still need an entry, and for which an entry is meaningful."""
        return self.filtered(lambda v: (
            not v.absorbed
            and not v.variance_move_id
            and not (v.currency_id or v.company_id.currency_id).is_zero(v.expensed_amount)
            and v._needs_journal_entry()
        ))

    def _needs_journal_entry(self):
        """A bill-driven variance under periodic valuation needs no entry.

        The closing entry drives the valuation account to ``total_value`` and
        the cost of sales follows implicitly, so posting on top would move the
        result twice. A landed cost needs one in both modes: its amount is
        parked in the freight expense account either way.
        """
        self.ensure_one()
        if self.origin == "recalc":
            return False
        if self.origin == "bill":
            return self.move_id.product_id.valuation == "real_time"
        return True

    def _post_company_reclassification(self):
        company = self.env.company
        aml_vals = []
        for categ, per_categ in self.grouped(
                lambda v: v.move_id.product_id.categ_id).items():
            accounts = categ.with_company(company)._variance_accounts()
            for origin, rows in per_categ.grouped("origin").items():
                amount = sum(rows.mapped("expensed_amount"))
                if company.currency_id.is_zero(amount):
                    continue
                aml_vals += self._reclassification_aml_vals(
                    origin, accounts, amount, categ)
        if not aml_vals:
            raise UserError(_("Nothing to reclassify for company %s.", company.display_name))

        date = fields.Date.context_today(self)
        violations = company._get_lock_date_violations(date)
        if violations:
            raise UserError(_(
                "The reclassification cannot be dated %(date)s: %(locks)s. "
                "Post it in an open period.",
                date=date,
                locks=", ".join(company._format_lock_dates(violations)),
            ))

        move = self.env["account.move"].create({
            "move_type": "entry",
            "date": date,
            "ref": _("Stock value variance reclassification"),
            "journal_id": company.account_stock_journal_id.id
            or self.env["account.journal"].search(
                [("type", "=", "general"), ("company_id", "=", company.id)], limit=1).id,
            "line_ids": [Command.create(vals) for vals in aml_vals],
        })
        move._post()
        self.variance_move_id = move.id
        return move

    def _reclassification_aml_vals(self, origin, accounts, amount, categ):
        """Where the amount sits decides the counterpart.

        ``landed_cost``: it never entered inventory -- it stayed in the freight
        expense account -- so it goes through inventory first and out again,
        which is the PCGE dynamic (20/61 then 69/20).

        ``bill``: the bill's own entry already moved the valuation account, so
        the amount is sitting in inventory and only has to come out (69/20).
        """
        label = _("%(categ)s - value variance (%(origin)s)",
                  categ=categ.display_name, origin=origin)
        valuation, variation, cogs = (
            accounts["valuation"], accounts["variation"], accounts["cogs"])

        def pair(debit_account, credit_account, value):
            sign = 1 if value > 0 else -1
            magnitude = abs(value)
            return [
                {"name": label, "account_id": debit_account.id,
                 "debit": magnitude if sign > 0 else 0.0,
                 "credit": 0.0 if sign > 0 else magnitude},
                {"name": label, "account_id": credit_account.id,
                 "credit": magnitude if sign > 0 else 0.0,
                 "debit": 0.0 if sign > 0 else magnitude},
            ]

        if origin == "landed_cost":
            return pair(valuation, variation, amount) + pair(cogs, valuation, amount)
        return pair(cogs, valuation, amount)

    # ------------------------------------------------------------------
    def _ledger_signed_amount(self):
        """What this row currently contributes to a valued ledger."""
        self.ensure_one()
        return 0.0 if self.absorbed else self.ledger_amount

    @api.model
    def _ledger_amount_for(self, move, expensed_amount):
        """Sign the ledger effect of a revaluation variance.

        Incoming move: the revaluation inflated the receipt by the whole amount
        while only the capitalised part belongs to the stock still there, so the
        ledger gives ``expensed`` back.

        Outgoing move: the revaluation inflated the *exit*, taking out value
        that was never inventory, so the ledger gives it back the other way.
        """
        return expensed_amount if move.is_out else -expensed_amount
