import logging

from odoo import api, models
from odoo.tools import float_is_zero

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    """category account resolution for the *native* valuation entry.

    Design rule of this file: never build, never remove, never post anything.
    Every hook calls ``super()`` first and only rewrites the account of a line
    when the native result has exactly the shape it knows. Anything unexpected -
    a renamed field, a changed number of lines, a missing account - makes the
    override step aside and return the native result untouched.
    """

    _inherit = "stock.move"

    # -------------------------------------------------------------------------
    # AVAILABILITY OF THE NATIVE MECHANISM WE PLUG INTO
    # -------------------------------------------------------------------------

    @api.model
    def _reclass_native_valuation_available(self):
        """Whether the native pieces this module relies on are still there."""
        return (
            "valuation_account_id" in self.env["stock.location"]._fields
            and hasattr(self.env["product.product"], "_get_product_accounts")
        )

    def _reclass_get_stock_valuation_account(self):
        """Native stock valuation account of the product, or empty."""
        self.ensure_one()
        accounts = self.product_id._get_product_accounts()
        return accounts.get("stock_valuation") or self.env["account.account"]

    # -------------------------------------------------------------------------
    # SCOPE AND PRIORITY
    # -------------------------------------------------------------------------

    def _reclass_location_uses_category_account(self, location):
        """Whether the category account may take part in this move.

        Manufacturing only: anything moving in or out of a production location,
        that is component consumptions and finished goods.

        Everything else keeps the native behaviour untouched, *including* the
        native decision of booking nothing: purchase receipts, sale deliveries,
        internal transfers, inventory adjustments and scrap.

        Scrap is left out on purpose. Odoo 19 gives no way to tell a scrap
        location from an inventory adjustment one - both are
        ``usage='inventory'``, the old ``scrap_location`` flag is gone and scrap
        simply defaults to the first such location - so covering that usage would
        silently drag inventory adjustments along. Rather than guess, the whole
        usage stays native.

        Override this single method to widen the scope.
        """
        self.ensure_one()
        return location.usage == "production"

    # -------------------------------------------------------------------------
    # RESOLUTION
    # -------------------------------------------------------------------------

    def _reclass_get_counterpart_location(self):
        """Location whose account the native entry uses as counterpart."""
        self.ensure_one()
        if self.location_id.valuation_account_id:
            return self.location_id
        if self.location_dest_id.valuation_account_id:
            return self.location_dest_id
        # Neither side carries an account: the counterpart is the non-valued one.
        if self.is_in:
            return self.location_id
        if self.is_out:
            return self.location_dest_id
        return self.env["stock.location"]

    def _reclass_get_category_account(self):
        """Production/consumption account for the product of this move, or empty.

        Resolution: the product itself, then its category and the ancestors of
        that category. The location is the caller's fallback.
        """
        self.ensure_one()
        product = self.product_id
        if not product:
            return self.env["account.account"]
        return product.with_company(self.company_id)._reclass_get_production_account()

    def _reclass_resolve_counterpart(self):
        """Resolve the counterpart account of the native entry.

        Every move resolves on its own: several moves of the same transfer end up
        in a single native entry, each one with the account of its own product
        category.

        :return: tuple ``(account, location)``. ``account`` is empty when the
                 native resolution must stand untouched.
        """
        self.ensure_one()
        empty = self.env["account.account"]
        if not self._reclass_native_valuation_available():
            return empty, self.env["stock.location"]
        location = self._reclass_get_counterpart_location()
        if not location or not self._reclass_location_uses_category_account(location):
            return empty, location
        # The category is the finer signal: the nature of what is consumed or
        # produced drives 60/61/71 per family of products. Without it, the native
        # account of the production location stands.
        return (
            self._reclass_get_category_account() or location.valuation_account_id
        ), location

    # -------------------------------------------------------------------------
    # NATIVE OVERRIDES
    # -------------------------------------------------------------------------

    def _should_create_account_move(self):
        """Let the category account rescue an entry the native flow would drop.

        Natively, a location without ``valuation_account_id`` means no entry at
        all. When the product category (or an ancestor) defines the category account,
        that account takes the place of the missing one and the entry is created.

        Every other native guard is kept: non-storable products, non-valued
        moves, zero quantity and periodic valuation still produce no entry. The
        rescue also stands down when the native line builder does not produce the
        shape this module knows how to complete, so an unknown future shape means
        native silence rather than a malformed entry.
        """
        if super()._should_create_account_move():
            return True
        try:
            return self._reclass_should_rescue_account_move()
        except Exception:  # noqa: BLE001 - a custom account must never break a transfer
            _logger.exception(
                "Reclassification rescue skipped for stock move %s: native decision kept", self.id)
            return False

    def _reclass_should_rescue_account_move(self):
        """Whether the category account must rescue an entry native would drop."""
        self.ensure_one()
        if not self._reclass_native_valuation_available():
            return False
        account, location = self._reclass_resolve_counterpart()
        if not account or location.valuation_account_id:
            return False
        # Mirror of the native guards (stock_account.StockMove
        # _should_create_account_move) minus the location-account one, which the
        # category account is precisely replacing.
        native_guards = (
            self.product_id.is_storable
            and self.is_valued
            and not float_is_zero(self.quantity, precision_rounding=self.product_uom.rounding)
            and self.product_id.valuation == "real_time"
        )
        if not native_guards:
            return False
        return bool(self._reclass_split_rescued_vals(super()._get_account_move_line_vals()))

    def _reclass_split_rescued_vals(self, vals_list):
        """Identify the two lines of a rescued entry.

        :return: tuple ``(line_without_account, line_with_stock_valuation)`` when
                 the native result has the canonical shape, ``()`` otherwise.
        """
        self.ensure_one()
        valuation_account = self._reclass_get_stock_valuation_account()
        if not valuation_account or len(vals_list) != 2:
            return ()
        missing = [vals for vals in vals_list if not vals.get("account_id")]
        valued = [
            vals for vals in vals_list
            if vals.get("account_id") == valuation_account.id
        ]
        if len(missing) != 1 or len(valued) != 1:
            return ()
        return missing[0], valued[0]

    def _get_account_move_line_vals(self):
        """Redirect the counterpart account of the native entry.

        Nothing is added and nothing is removed: the native entry keeps its two
        lines, its amount and its direction. Only the account that would come
        from the location is replaced, following ``_reclass_resolve_counterpart()``.
        """
        vals_list = super()._get_account_move_line_vals()
        if not self._reclass_native_valuation_available():
            return vals_list
        try:
            return self._reclass_apply_account_override(vals_list)
        except Exception:  # noqa: BLE001 - a custom account must never break a transfer
            _logger.exception(
                "category account override skipped for stock move %s: native accounts kept",
                self.id,
            )
            return vals_list

    def _reclass_apply_account_override(self, vals_list):
        """Rewrite the counterpart account in ``vals_list``, in place."""
        self.ensure_one()
        account, location = self._reclass_resolve_counterpart()
        if not account:
            return vals_list
        valuation_account = self._reclass_get_stock_valuation_account()
        location_account = location.valuation_account_id

        if location_account:
            if account == location_account or location_account == valuation_account:
                # Nothing to redirect, or a degenerate setup where both sides of
                # the native entry share the same account.
                return vals_list
            targets = [
                vals for vals in vals_list
                if vals.get("account_id") == location_account.id
            ]
            if len(targets) != 1:
                _logger.info(
                    "Reclassification: unexpected native entry shape for stock move %s "
                    "(%s lines on the location account); native accounts kept",
                    self.id, len(targets),
                )
                return vals_list
            return self._reclass_replace_counterpart(vals_list, targets[0], account)

        # Rescued entry: the native builder left the counterpart line without an
        # account, and picked its outgoing branch because no location carried
        # one. Put the accounts back on the right side of the entry.
        canonical = self._reclass_split_rescued_vals(vals_list)
        if not canonical:
            # Should not happen: _should_create_account_move only rescues a
            # canonical shape. Fill whatever is missing so the entry stays valid.
            _logger.warning(
                "Reclassification: unexpected native entry shape while rescuing stock move %s",
                self.id,
            )
            for vals in vals_list:
                if not vals.get("account_id"):
                    vals["account_id"] = account.id
            return vals_list
        missing, valued = canonical
        if self.is_in:
            missing["account_id"] = valuation_account.id
            return self._reclass_replace_counterpart(vals_list, valued, account)
        return self._reclass_replace_counterpart(vals_list, missing, account)

    # -------------------------------------------------------------------------
    # COUNTERPART EXTENSION POINT
    # -------------------------------------------------------------------------

    def _reclass_replace_counterpart(self, vals_list, counterpart_vals, account):
        """Substitute the counterpart line by whatever ``_reclass_counterpart_lines``
        returns, keeping its position in the entry."""
        self.ensure_one()
        replacement = self._reclass_counterpart_lines(counterpart_vals, account)
        index = next(
            i for i, vals in enumerate(vals_list) if vals is counterpart_vals)
        vals_list[index:index + 1] = replacement
        return vals_list

    def _reclass_counterpart_lines(self, counterpart_vals, account):
        """Lines replacing the counterpart line of the native entry.

        Base implementation: a single line, with the resolved account applied.
        The manufacturing bridge overrides this to break the counterpart down by
        cost origin (consumables, operations, materials) when it can prove how
        the cost was composed.

        :return: list of line vals; must keep the same total amount and side.
        """
        self.ensure_one()
        counterpart_vals["account_id"] = account.id
        return [counterpart_vals]
