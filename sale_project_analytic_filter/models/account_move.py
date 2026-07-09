# Copyright 2026 Ganemo
# License OPL-1 (Odoo Proprietary License v1.0) - See LICENSE file.
from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _stock_account_prepare_realtime_out_lines_vals(self):
        """Strip the project analytic from the COGS stock valuation line.

        The anglo-saxon Cost of Goods Sold journal items are created with
        their ``analytic_distribution`` passed *explicitly in the create
        vals* (``stock_account`` copies it from the invoice product line,
        which ``sale_project`` has already stamped with the project's
        distribution). Because the value is supplied, the ORM never triggers
        ``account.move.line._compute_analytic_distribution`` for these lines
        -- a supplied value short-circuits the compute of a stored, editable
        computed field. Clearing the valuation line in that compute is
        therefore not enough; it has to happen on the vals themselves, before
        ``create``.

        Note this depends on the exact Odoo 19 build: some builds stamp the
        analytic on *both* COGS lines (the bug this module fixes), while
        others only stamp the expense line. The correction is therefore
        self-neutralizing -- on a build that already leaves the valuation
        line clean, there is simply nothing to strip.
        """
        vals_list = super()._stock_account_prepare_realtime_out_lines_vals()
        return self._strip_cogs_valuation_analytic(vals_list)

    def _strip_cogs_valuation_analytic(self, vals_list):
        """Clear ``analytic_distribution`` on every COGS vals booked on the
        product's stock valuation account, when the per-company correction is
        enabled.

        The stock valuation account is the inventory counterpart of the COGS
        pair and must not carry analytic, while its expense counterpart does.
        This mirrors the account ``stock_analytic_distribution`` excludes on
        the inventory valuation entry, so the criterion is consistent across
        the suite.
        """
        for vals in vals_list:
            if vals.get("display_type") != "cogs" or not vals.get(
                "analytic_distribution"
            ):
                continue
            company = self.browse(vals["move_id"]).company_id
            if not company.cogs_analytic_exclude_valuation:
                continue
            product = self.env["product.product"].browse(vals.get("product_id"))
            if not product:
                continue
            # Resolve the stock valuation account exactly as the upstream COGS
            # preparation does (fiscal-position aware, per company), so we
            # match the very account it booked the valuation line on.
            move = self.browse(vals["move_id"])
            accounts = product.product_tmpl_id.with_company(
                company
            ).get_product_accounts(fiscal_pos=move.fiscal_position_id)
            valuation_account = accounts.get("stock_valuation")
            if valuation_account and vals.get("account_id") == valuation_account.id:
                vals["analytic_distribution"] = False
        return vals_list
