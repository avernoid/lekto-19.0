import logging

from odoo import models

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    """Break the counterpart of the manufacturing entry down by cost origin.

    Nothing is created and no amount changes: the entry keeps the same total and
    the same direction. The single counterpart line becomes several, one per
    origin of the cost, each on its own account.

    The split is only applied when the composition of the cost can be *proved*
    (see ``_reclass_mrp_breakdown``). Anything else -- a standard-cost product, an
    unexpected shape, an exception -- falls back to the single line the module
    already produced.
    """

    _inherit = "stock.move"

    # -------------------------------------------------------------------------
    # THE LABOUR ENTRY THIS SPLIT HAS TO AGREE WITH
    # -------------------------------------------------------------------------

    def _reclass_production_location_account(self, production):
        """Valuation account of the production location, or empty.

        It is the last step of the resolution chain and the account the native
        labour entry debits -- ``mrp_account.mrp_production._post_labour()`` skips
        the entry entirely when the location has none.
        """
        location = production.product_id.with_company(
            production.company_id).property_stock_production
        return location.valuation_account_id

    def _reclass_operations_by_account(self, production, default_account):
        """Work centre cost of the order, on the account the configuration resolves.

        **One** account for every work order, chosen like every other account of
        this module: product, then its category chain, then the account of the
        production location. The flag that suppresses the labour entry decides
        whether that entry exists, never where this credit goes.

        The consequence is deliberate: configuring an operations account while the
        labour entry is still posted leaves its debit on the production location.
        That is a configuration decision -- the field help spells it out -- and not
        something guessed here; obeying the configuration is the point.

        Amounts are rounded **per work order**, exactly like ``_post_labour`` does,
        so when both entries do share an account they agree to the cent.
        """
        currency = production.company_id.currency_id
        account = (
            self.product_id.with_company(
                self.company_id)._reclass_get_operations_account()
            or self._reclass_production_location_account(production)
            or default_account
        )
        if not account:
            return {}
        total = sum(
            currency.round(workorder._cal_cost())
            for workorder in production.workorder_ids
        )
        if currency.is_zero(total):
            return {}
        return {account: total}

    def _reclass_consumables_by_account(self, production, default_account):
        """Value of the non-storable components, grouped by their own account.

        Each consumable resolves its own recognition account (product, then its
        category chain); components that resolve the same one are added together,
        and those that resolve none fall to the caller's default so their value is
        never lost.
        """
        amounts = {}
        for raw in production.move_raw_ids.filtered(
                lambda move: move.state == "done" and not move.product_id.is_storable):
            if not raw.value:
                continue
            account = raw.product_id.with_company(
                self.company_id)._reclass_get_recognition_account() or default_account
            if not account:
                continue
            amounts[account] = amounts.get(account, 0.0) + raw.value
        return amounts

    # -------------------------------------------------------------------------
    # COST COMPOSITION
    # -------------------------------------------------------------------------

    def _reclass_mrp_output_moves(self, production):
        """Output moves already posted for this order (finished goods + byproducts)."""
        return (production.move_finished_ids | production.move_byproduct_ids).filtered(
            lambda move: move.state == "done")

    def _reclass_mrp_extra_cost(self, production, output_moves):
        """``extra_cost`` of the order, expressed for the batch.

        Native ``_cal_price`` applies it as ``extra_cost * quantity`` of the moves
        of the manufactured product, byproducts excluded.
        """
        quantity = 0.0
        for move in output_moves:
            if move.product_id == production.product_id:
                quantity += move.product_uom._compute_quantity(
                    move.quantity, move.product_id.uom_id)
        return production.extra_cost * quantity

    def _reclass_mrp_breakdown(self, default_account):
        """Cost origins of this manufacturing order, for the whole batch.

        :return: dict ``{'total': float, 'origins': {account: amount}}`` or ``{}``
                 when the composition cannot be proved.

        The invariant checked here is the one Odoo itself applies in
        ``mrp_account._cal_price()``::

            raw values + work centre cost + extra cost == value of the outputs

        Verified against a plain order, a backorder (both batches), a byproduct
        taking a cost share, and a standard-cost product -- where it does NOT hold,
        which is exactly why it is checked instead of assumed.

        Note that the figures are read from the whole order, not from the batch
        being posted. Native splits an order into one record per batch
        (``_split_productions``), so in the standard flow they are the same set;
        where they are not, this invariant fails and the split stands down.
        """
        self.ensure_one()
        production = self.production_id
        if not production:
            return {}
        currency = self.company_id.currency_id
        if not currency:
            return {}

        outputs = self._reclass_mrp_output_moves(production)
        if self not in outputs:
            return {}
        raws = production.move_raw_ids.filtered(lambda move: move.state == "done")

        storables = sum(move.value for move in raws if move.product_id.is_storable)
        consumables_total = sum(
            move.value for move in raws if not move.product_id.is_storable)
        # Unrounded, like _cal_price: this is what has to reconcile with the value
        # of the outputs. The per-account amounts below are rounded like the labour
        # entry, and the difference lands in the remainder.
        operations_total = sum(
            workorder._cal_cost() for workorder in production.workorder_ids)
        extra = self._reclass_mrp_extra_cost(production, outputs)
        total = sum(move.value for move in outputs)

        composed = storables + consumables_total + operations_total + extra
        if not currency.is_zero(composed - total):
            _logger.info(
                "Reclassification: the cost of %s does not decompose "
                "(inputs %s vs outputs %s); native counterpart kept",
                production.name, composed, total)
            return {}
        if currency.compare_amounts(total, 0.0) <= 0:
            return {}

        origins = self._reclass_consumables_by_account(production, default_account)
        for account, amount in self._reclass_operations_by_account(
                production, default_account).items():
            origins[account] = origins.get(account, 0.0) + amount
        if any(currency.compare_amounts(amount, 0.0) < 0 for amount in origins.values()):
            return {}
        if currency.compare_amounts(sum(origins.values()), total) > 0:
            return {}
        return {"total": total, "origins": origins}

    # -------------------------------------------------------------------------
    # SPLIT
    # -------------------------------------------------------------------------

    def _reclass_counterpart_lines(self, counterpart_vals, account):
        single = super()._reclass_counterpart_lines(counterpart_vals, account)
        try:
            split = self._reclass_mrp_counterpart_lines(counterpart_vals, account)
        except Exception:  # noqa: BLE001 - costing must never break a transfer
            _logger.exception(
                "Reclassification: cost breakdown skipped for stock move %s; "
                "single counterpart kept", self.id)
            return single
        return split or single

    def _reclass_mrp_counterpart_lines(self, counterpart_vals, account):
        """Build the split lines, or ``[]`` to keep the single line."""
        self.ensure_one()
        breakdown = self._reclass_mrp_breakdown(account)
        if not breakdown:
            return []

        currency = self.company_id.currency_id
        amount = abs(self._reclass_counterpart_amount(counterpart_vals))
        # This move's share of the batch: byproducts take their cost share, so
        # every origin is prorated by the same ratio.
        share = self.value / breakdown["total"] if breakdown["total"] else 0.0

        grouped = {}
        for origin_account, origin_amount in breakdown["origins"].items():
            prorated = currency.round(origin_amount * share)
            if currency.is_zero(prorated):
                continue
            grouped[origin_account] = grouped.get(origin_account, 0.0) + prorated

        # The remainder -- storable materials, extra cost and any rounding, both of
        # the proration and of the per-work-order rounding -- is taken by
        # difference, so the entry always balances to the cent.
        remainder = currency.round(amount - sum(grouped.values()))
        if currency.compare_amounts(remainder, 0.0) < 0:
            _logger.info(
                "Reclassification: negative remainder on stock move %s; "
                "single counterpart kept", self.id)
            return []
        if not currency.is_zero(remainder) or not grouped:
            grouped[account] = grouped.get(account, 0.0) + remainder

        if len(grouped) == 1 and next(iter(grouped)) == account:
            # Same single line the base module already produced.
            return []
        return [
            self._reclass_counterpart_line_vals(counterpart_vals, origin_account, line_amount)
            for origin_account, line_amount in grouped.items()
        ]

    def _reclass_counterpart_amount(self, counterpart_vals):
        """Signed amount carried by the counterpart line."""
        return counterpart_vals.get("debit", 0.0) or -counterpart_vals.get("credit", 0.0)

    def _reclass_counterpart_line_vals(self, counterpart_vals, account, amount):
        """Copy of the counterpart line with its own account and share."""
        vals = dict(counterpart_vals)
        vals["account_id"] = account.id
        if counterpart_vals.get("debit"):
            vals["debit"], vals["credit"] = amount, 0.0
        else:
            vals["debit"], vals["credit"] = 0.0, amount
        return vals
