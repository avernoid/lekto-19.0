import logging

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools import float_is_zero

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    # ------------------------------------------------------------------
    # Recalculation
    # ------------------------------------------------------------------
    def _recalculate_valuation_waterfall(
        self, product_id, start_date, initial_qty, initial_value,
        new_standard_price=None, company=None, mode="adjust",
    ):
        """Replay AVCO from a point in time and correct the outgoing moves.

        Two modes, and the difference is what gets written:

        ``adjust`` (default)
            Records the per-move correction as a variance row and leaves
            ``stock.move.value`` alone.  The native value survives next to the
            correction, the operation is reversible, and -- because nothing in
            core reads a variance row -- it does not drag the whole valuation
            dependency graph behind every write.  Writing ``value`` fans out
            through ``product_id.stock_move_ids`` and touches every move of the
            product, per write.

        ``restate``
            The historical behaviour: overwrite ``stock.move.value``.  For real
            corruption of the underlying data, where the number itself is wrong
            and the accounts depend on it.  Rewrites history, so it is never the
            default.
        """
        if mode not in ("adjust", "restate"):
            raise UserError(_("Unknown recalculation mode: %s", mode))

        company = company or self.env.company
        product = self.env["product.product"].browse(product_id).with_company(company)

        # cost_method is company-dependent, so it has to be read in the company
        # being recalculated, not in whichever one the user happens to be in.
        if product.cost_method != "average":
            raise UserError(_(
                "Recalculation aborted: %(product)s is configured as "
                "'%(method)s' in %(company)s (expected 'average').",
                product=product.display_name, method=product.cost_method,
                company=company.display_name,
            ))

        if new_standard_price and mode != "restate":
            # Forcing a standard price is a raw-SQL write that deliberately
            # bypasses the ORM so no native revaluation fires.  That belongs to
            # a restatement: in adjust mode nothing is restated, and mutating
            # the engine's own number with no correction to match would be a
            # silent change of exactly the kind this mode exists to avoid.
            raise UserError(_(
                "A new standard price can only be forced when restating "
                "values. In adjustment mode the correction is recorded beside "
                "the movement and the product cost is left to Odoo."))

        rounding = product.uom_id.rounding
        running_qty = initial_qty
        running_value = initial_value

        moves = self.search([
            ("product_id", "=", product.id),
            ("company_id", "=", company.id),
            ("date", ">=", start_date),
            ("state", "=", "done"),
        ], order="date asc, id asc")

        audit_details = []
        if mode == "restate":
            audit_details += self._recalc_clear_product_values(
                product, company, start_date)
            if new_standard_price:
                self._set_standard_price_safe(product, new_standard_price, company)

        # The returns branch needs the corrected value of the move being
        # returned.  In restate mode that used to come from re-reading
        # ``origin.value``, which the loop had just overwritten; in adjust mode
        # nothing is overwritten, so the corrected values are carried here.
        corrected_value = {}
        moves_affected = 0
        total_correction = 0.0

        absorbed = self.env["stock.value.variance"]
        for move in moves:
            if not move.is_in and not move.is_out:
                continue

            # Valued quantity, in the product's unit.  ``move.quantity`` is in
            # the move's own unit, and mixing it with ``value`` (always in the
            # product's) is a factor-sized error on any move booked in a
            # different UoM.
            valued_qty = move._get_valued_qty()

            if move.is_in:
                value_in = move.value
                if move.origin_returned_move_id:
                    origin = move.origin_returned_move_id
                    origin_qty = origin._get_valued_qty()
                    if not float_is_zero(origin_qty, precision_rounding=rounding):
                        origin_value = corrected_value.get(origin.id, origin.value)
                        restored = valued_qty * (origin_value / origin_qty)
                        if abs(value_in - restored) > 0.01:
                            moves_affected += 1
                            total_correction += abs(value_in - restored)
                            value_in = restored
                            corrected_value[move.id] = restored
                            self._recalc_write(move, restored, mode, company)
                            audit_details.append(self._recalc_detail(move, restored))

                # A landed cost or bill variance on an incoming move corrects the
                # ledger for goods that had already gone.  The replay pushes that
                # same money into the outgoing moves instead, so leaving both
                # alive would correct it twice.
                absorbed |= move.variance_line_ids.filtered(
                    lambda v: v.origin != "recalc" and not v.absorbed)

                running_qty += valued_qty
                running_value += value_in
                continue

            if running_qty <= 0 or float_is_zero(running_qty, precision_rounding=rounding):
                unit_cost = product.standard_price
            else:
                unit_cost = running_value / running_qty
            target = valued_qty * unit_cost

            if abs(move.value - target) > 0.01:
                moves_affected += 1
                total_correction += abs(move.value - target)
                corrected_value[move.id] = target
                self._recalc_write(move, target, mode, company)
                audit_details.append(self._recalc_detail(move, target))

            running_qty -= valued_qty
            running_value -= target

        if absorbed:
            absorbed.absorbed = True

        final_cost = product.standard_price
        if running_qty > 0 and mode == "restate":
            final_cost = running_value / running_qty
            self._set_standard_price_safe(product, final_cost, company)

        return {
            "moves_count": moves_affected,
            "total_correction": total_correction,
            "final_qty": running_qty,
            "final_value": running_value,
            "final_cost": final_cost,
            "details": audit_details,
            "absorbed_count": len(absorbed),
        }

    # ------------------------------------------------------------------
    def _recalc_write(self, move, target, mode, company):
        """Apply one move's correction, according to the mode."""
        if mode == "restate":
            valued_qty = move._get_valued_qty()
            move.write({
                "value": target,
                "price_unit": target / valued_qty if valued_qty else 0.0,
            })
            return

        correction = target - move.value
        # An outgoing move that must cost more takes the ledger down; an
        # incoming one that must be worth more takes it up.
        ledger_amount = -correction if move.is_out else correction
        existing = move.variance_line_ids.filtered(lambda v: v.origin == "recalc")
        vals = {
            "move_id": move.id,
            "company_id": company.id,
            "origin": "recalc",
            "date": move.date,
            "base_amount": correction,
            "capitalized_amount": 0.0,
            "expensed_amount": correction,
            "ledger_amount": ledger_amount,
            "valued_qty": move._get_valued_qty(),
            "remaining_qty": 0.0,
        }
        if existing:
            # Replace rather than accumulate: a second run over the same window
            # must reproduce the same correction, not double it.
            existing[1:].unlink()
            existing[0].write(vals)
        else:
            self.env["stock.value.variance"].sudo().create(vals)

    def _recalc_detail(self, move, target):
        """Snapshot for the audit: without the previous value there is no undo
        and no way to show an auditor what changed."""
        return (0, 0, {
            "move_id": move.id,
            "previous_value": move.value,
            "new_value": target,
        })

    def _recalc_clear_product_values(self, product, company, cutoff_date):
        """Drop the standard-price anchors the restated history contradicts.

        Narrow on purpose.  The original domain matched on product and date
        alone, under ``sudo()``, which in a multi-company database deleted other
        companies' price history for the same product and silently moved their
        AVCO anchor.  It also swept the per-move manual valuations that
        ``_get_manual_value`` reads with top priority -- deleting those unpins a
        move that somebody pinned deliberately -- and the per-lot anchors.
        """
        values = self.env["product.value"].sudo().search([
            ("product_id", "=", product.id),
            ("company_id", "=", company.id),
            ("move_id", "=", False),
            ("lot_id", "=", False),
            ("date", ">=", cutoff_date),
        ])
        if not values:
            return []
        details = [
            (0, 0, {
                "deleted_product_value_date": value.date,
                "previous_value": value.value,
                "new_value": 0.0,
            })
            for value in values
        ]
        _logger.info(
            "stock_valuation_avco_recalc: deleting %s product.value anchors for "
            "%s in %s from %s", len(values), product.display_name,
            company.display_name, cutoff_date)
        values.unlink()
        return details

    def _set_standard_price_safe(self, product, new_price, company=None):
        """Write standard_price by SQL, bypassing Odoo 19's automatic
        revaluation on ORM write.  Company-dependent, hence JSONB keyed by id."""
        import json

        company = company or self.env.company
        field = product._fields.get("standard_price")
        is_jsonb = field.company_dependent if field else False

        cr = self.env.cr
        cr.execute("SELECT standard_price FROM product_product WHERE id = %s",
                   (product.id,))
        row = cr.fetchone()
        if not row:
            return

        if is_jsonb:
            raw = row[0]
            current = {}
            if isinstance(raw, dict):
                current = raw
            elif isinstance(raw, str):
                try:
                    current = json.loads(raw)
                except ValueError:
                    current = {}
            current[str(company.id)] = new_price
            cr.execute(
                "UPDATE product_product SET standard_price = %s WHERE id = %s",
                (json.dumps(current), product.id))
        else:
            cr.execute(
                "UPDATE product_product SET standard_price = %s WHERE id = %s",
                (new_price, product.id))
        product.invalidate_recordset(["standard_price"])

    @api.model
    def _get_historical_balance_at_date(self, product_id, cutoff_date, company=None,
                                        mode="adjust"):
        """Opening balance strictly before ``cutoff_date``.

        In adjust mode the corrections live in variance rows rather than in
        ``value``, so a genesis built from ``value`` alone would ignore every
        correction a previous run made and a second run with a different window
        would start from the wrong number.
        """
        company = company or self.env.company
        adjustment = """
            + COALESCE((
                SELECT SUM(v.ledger_amount) FROM stock_value_variance v
                 WHERE v.move_id = stock_move.id AND NOT v.absorbed
            ), 0.0)
        """ if mode == "adjust" else ""
        query = f"""
            SELECT
                SUM(CASE WHEN is_in THEN quantity ELSE -quantity END) AS total_qty,
                SUM(CASE WHEN is_in THEN value ELSE -value END {adjustment}) AS total_value
            FROM stock_move
            WHERE product_id = %s
              AND company_id = %s
              AND state = 'done'
              AND date < %s
              AND (is_in = TRUE OR is_out = TRUE)
        """
        self.env.cr.execute(query, (product_id, company.id, cutoff_date))
        res = self.env.cr.dictfetchone()
        return (res.get("total_qty") or 0.0), (res.get("total_value") or 0.0)
