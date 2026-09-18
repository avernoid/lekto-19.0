from odoo import api, models


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.depends(
        "variance_line_ids.ledger_amount",
        "variance_line_ids.absorbed",
        "variance_line_ids.kind",
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
        """What the movement is worth on top of its stored value.

        Since stock_landed_cost_variance 19.0.2 a late revaluation is folded into
        the stored ``value`` itself (exits restated, returns re-derived), so those
        rows add nothing here. What remains are the amounts no movement value can
        carry: the value Odoo's average replay drops when goods arrive on negative
        stock, recorded as live rows on the entry where it happens.

        The quantity part of the hook is no longer meaningful -- no row describes
        units gone at a revaluation any more -- and returns 0.
        """
        self.ensure_one()
        rows = self.variance_line_ids.filtered(lambda r: r.kind != "legacy")
        return sum(row._ledger_signed_amount() for row in rows), 0.0
