from odoo import api, models


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.depends(
        "variance_line_ids.ledger_amount",
        "variance_line_ids.absorbed",
        "variance_line_ids.valued_qty",
        "variance_line_ids.remaining_qty",
    )
    def _compute_kardex_variance(self):
        """Re-declare the dependencies now that the real source exists.

        The base module cannot name ``variance_line_ids`` -- the model behind it
        needs ``stock_landed_costs``, which the columns deliberately do not.
        Odoo resolves a computed field's dependencies through the method it
        finds on the class, so overriding here extends them; the base ones stay
        because ``super()`` still carries them.
        """
        return super()._compute_kardex_variance()

    def _kardex_variance_amounts(self):
        """Sum what the recorded variances say this move is really worth.

        Each row already carries its ledger effect signed, so nothing here has
        to know that an incoming move gives the amount back while an outgoing
        one gives it back the other way.  Absorbed rows contribute zero: a
        valuation recalculation folded them into the values already, and
        counting both would correct the same money twice.
        """
        self.ensure_one()
        rows = self.variance_line_ids
        if not rows:
            return 0.0, 0.0
        amount = sum(row._ledger_signed_amount() for row in rows)
        # Informative: how much had already gone when the move was last
        # revalued. The most recent live row is the meaningful snapshot -- an
        # older one describes a warehouse state that no longer applies.
        live = rows.filtered(lambda r: not r.absorbed).sorted("date")
        qty = (live[-1].valued_qty - live[-1].remaining_qty) if live else 0.0
        return amount, qty
