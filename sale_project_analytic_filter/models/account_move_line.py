# Copyright 2026 Ganemo
# License OPL-1 (Odoo Proprietary License v1.0) - See LICENSE file.
from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _compute_analytic_distribution(self):
        """Reimpose the native invariant after upstream computation.

        ``sale_project`` (when a project is in the context) stamps the
        project's analytic distribution on every line that is not a
        receivable/payable account, including the COGS line booked on the
        product's stock valuation account. That line is the inventory
        counterpart of the Cost of Goods Sold pair, so it ends up carrying
        the same distribution as the expense line and the two cancel each
        other out in the project's analytic ledger.

        We let the standard computation run first, then strip the
        distribution from any COGS line booked on a stock valuation account.
        This mirrors the criterion used by ``stock_analytic_distribution`` on
        the inventory valuation entry (``_get_account_move_line_vals``): the
        stock valuation account is the one line that never carries analytic;
        its counterpart does.

        Self-neutralizing: when nothing mis-tags the stock valuation COGS
        line (e.g. Odoo fixes the upstream behaviour), ``misplaced`` is empty
        and this override does nothing.
        """
        super()._compute_analytic_distribution()
        misplaced = self.filtered(lambda line: line._cogs_analytic_is_misplaced())
        if misplaced:
            misplaced.analytic_distribution = False

    def _cogs_analytic_is_misplaced(self):
        """Whether this is a COGS line wrongly carrying analytic on the
        product's stock valuation account, with the correction enabled for
        its company.
        """
        self.ensure_one()
        if self.display_type != "cogs" or not self.analytic_distribution:
            return False
        if not self.company_id.cogs_analytic_exclude_valuation:
            return False
        if not self.product_id:
            return False
        # Same account that stock_account books the COGS counterpart on, and
        # the same one stock_analytic_distribution excludes on the valuation
        # entry -> single, consistent criterion across the suite.
        valuation_account = self.with_company(
            self.company_id
        ).product_id._get_product_accounts()["stock_valuation"]
        return bool(valuation_account) and self.account_id == valuation_account
