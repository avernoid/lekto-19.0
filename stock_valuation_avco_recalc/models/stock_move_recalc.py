import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    def _valuation_rebuild(self, product, company, date):
        """Bring the stored values of a product back to what Odoo's own engine gives them (design v4, §5).

        For history the late revaluation engine never saw: movements done before it was installed, or
        values damaged by hand.  It runs the same fold as every late revaluation
        (``stock_landed_cost_variance``): exits at the native replay cost in (date, id) order, customer
        returns re-derived with ``_set_value()``, the value the engine drops recorded as live rows.

        What it deliberately does NOT do, and why:

        * no journal entry -- a rebuild corrects history whose accounting was closed with other
          numbers; the differences are left visible for the accountant instead of posted by surprise;
        * no algorithm of its own -- the former waterfall differed from the core on negative stock and
          returns (parity tests: 2 of 3 failed);
        * no SQL write of the product cost -- the cost is refreshed with the native
          ``_update_standard_price``, which keeps it coherent with the engine;
        * no deletion of ``product.value`` anchors -- they are deliberate manual valuations.

        Every amount is recorded as a ``recalc`` row dated ``date``, so reports rebuild any period before
        that date exactly as it was filed.
        """
        product = product.with_company(company)
        Move = self.env["stock.move"].with_company(company)
        if product.cost_method not in ("average", "fifo"):
            raise UserError(_(
                "%(product)s uses the '%(method)s' costing method in %(company)s: there is no history "
                "to rebuild.", product=product.display_name, method=product.cost_method,
                company=company.display_name))
        moves = Move.search([("product_id", "=", product.id), ("company_id", "=", company.id),
                             ("state", "=", "done"), "|", ("is_in", "=", True), ("is_out", "=", True)])
        previous = {move.id: move.value for move in moves}

        deltas, return_deltas = Move._variance_fold(product)
        discard_rows = Move._variance_sync_discard_rows(product, date)

        product._update_standard_price()
        if product.lot_valuated:
            moves.move_line_ids.lot_id.with_company(company)._update_standard_price()

        when = fields.Datetime.to_datetime(date)
        vals, details = [], []
        for move_id, delta in list(deltas.items()) + list(return_deltas.items()):
            move = Move.browse(move_id)
            vals.append({
                "move_id": move.id, "company_id": company.id, "kind": "recalc", "date": when,
                "ledger_amount": -delta if move_id in deltas else delta, "absorbed": True,
                "valued_qty": move._get_valued_qty(),
            })
            details.append((0, 0, {"move_id": move.id, "previous_value": previous.get(move.id, 0.0),
                                   "new_value": move.value}))
        if vals:
            self.env["stock.value.variance"].sudo().create(vals)
        _logger.info("stock_valuation_avco_recalc: %s rebuilt in %s: %s movements, %s live rows",
                     product.display_name, company.display_name, len(vals), len(discard_rows))
        return {
            "moves_count": len(vals),
            "total_correction": sum(abs(v["ledger_amount"]) for v in vals),
            "live_rows": len(discard_rows),
            "details": details,
        }
