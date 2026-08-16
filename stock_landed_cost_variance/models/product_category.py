from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductCategory(models.Model):
    _inherit = "product.category"

    # Declared, never inferred.  The native field names do not carry their PCGE
    # role: on the Peruvian chart `account_stock_variation_id` points at 69121
    # (cost of sales) and `account_stock_expense_id` at 6111 (inventory
    # variation) -- the opposite of what the names suggest.
    variance_valuation_account_id = fields.Many2one(
        "account.account", string="Variance: Stock Valuation",
        company_dependent=True, check_company=True,
        help="Inventory account debited/credited when a value variance is "
             "reclassified. Usually the same stock valuation account.")
    variance_variation_account_id = fields.Many2one(
        "account.account", string="Variance: Inventory Variation",
        company_dependent=True, check_company=True,
        help="Inventory variation account used as the counterpart when the "
             "variance came from a landed cost.")
    variance_cogs_account_id = fields.Many2one(
        "account.account", string="Variance: Cost of Sales",
        company_dependent=True, check_company=True,
        help="Cost of sales account where the variance is finally recognised.")

    # ------------------------------------------------------------------
    def _variance_accounts(self):
        """Return the three accounts, or raise with a precise message.

        Never falls back to a native account: a silent fallback is how a
        reclassification ends up posted against the wrong side of the P&L.
        """
        self.ensure_one()
        missing = [
            label for label, account in (
                (_("Stock Valuation"), self.variance_valuation_account_id),
                (_("Inventory Variation"), self.variance_variation_account_id),
                (_("Cost of Sales"), self.variance_cogs_account_id),
            ) if not account
        ]
        if missing:
            raise UserError(_(
                "Product category '%(categ)s' has no variance account "
                "configured for: %(missing)s.",
                categ=self.display_name, missing=", ".join(missing),
            ))
        self._variance_check_accounts()
        return {
            "valuation": self.variance_valuation_account_id,
            "variation": self.variance_variation_account_id,
            "cogs": self.variance_cogs_account_id,
        }

    def _variance_check_accounts(self):
        """Refuse accounts the periodic closing sweeps.

        ``_get_continental_realtime_variation_vals`` reads the raw balance of
        whatever account sits in ``account_stock_variation_id`` and nets it out,
        so a reclassification posted there is cancelled line for line by the
        next closing, silently.
        """
        self.ensure_one()
        valuation_accounts = self.env["account.account"].search(
            [("account_stock_variation_id", "!=", False)])
        forbidden = (valuation_accounts.account_stock_variation_id
                     | valuation_accounts.account_stock_expense_id)
        clash = forbidden & self.variance_cogs_account_id
        if clash:
            raise UserError(_(
                "Account %(acc)s is used as a stock variation/expense account, "
                "so the periodic closing nets its balance out and would cancel "
                "the reclassification. Use a dedicated cost of sales account.",
                acc=clash[0].display_name,
            ))

    @api.onchange("property_stock_valuation_account_id")
    def _onchange_variance_defaults(self):
        """Propose, never apply silently."""
        for categ in self:
            valuation = categ.property_stock_valuation_account_id
            if valuation and not categ.variance_valuation_account_id:
                categ.variance_valuation_account_id = valuation
