# Copyright 2026 Ganemo
# License OPL-1 (Odoo Proprietary License v1.0) - See LICENSE file.
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import SQL
from odoo.tools.float_utils import float_compare


class StockMove(models.Model):
    _name = "stock.move"
    _inherit = ["stock.move", "analytic.mixin"]

    # Don't carry the distribution over when a transfer/move is duplicated:
    # it is a costing decision specific to the original operation.
    analytic_distribution = fields.Json(copy=False)

    # ------------------------------------------------------------------
    # Defaulting & propagation
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """Default the move distribution from its transfer header.

        Mirrors the way a move inherits its locations from the picking: the
        picking-level distribution is only a convenience default, a move can
        still hold its own.
        """
        for vals in vals_list:
            if not vals.get("analytic_distribution") and vals.get("picking_id"):
                picking = self.env["stock.picking"].browse(vals["picking_id"])
                if picking.analytic_distribution:
                    vals["analytic_distribution"] = picking.analytic_distribution
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if "analytic_distribution" in vals and not self.env.context.get(
            "skip_analytic_move_line_sync"
        ):
            # Keep the operation lines aligned with the move so the value shown
            # in the detailed operations matches what will be posted.
            self.move_line_ids.with_context(
                skip_analytic_move_sync=True
            ).write({"analytic_distribution": vals["analytic_distribution"]})
        return res

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        vals = super()._prepare_move_line_vals(
            quantity=quantity, reserved_quant=reserved_quant
        )
        if self.analytic_distribution:
            vals["analytic_distribution"] = self.analytic_distribution
        return vals

    def _prepare_procurement_values(self):
        """Carry the distribution along the procurement chain (MTO, pull rules)."""
        vals = super()._prepare_procurement_values()
        if self.analytic_distribution:
            vals["analytic_distribution"] = self.analytic_distribution
        return vals

    # ------------------------------------------------------------------
    # Accounting: stamp the distribution on the valuation entry
    # ------------------------------------------------------------------
    def _get_account_move_line_vals(self):
        """Add the analytic distribution to the counterpart valuation line.

        We only enrich the journal items that Odoo already decided to create:
        if native valuation does not post an entry (e.g. periodic valuation),
        this override never runs and nothing is created.

        The line booked on the product's stock valuation account is left
        untouched; the counterpart line carries the distribution. Posting the
        entry then lets Odoo create and link the analytic items by itself.
        """
        vals_list = super()._get_account_move_line_vals()
        distribution = self.analytic_distribution
        if not distribution:
            return vals_list
        valuation_account = self.with_company(
            self.company_id
        ).product_id._get_product_accounts()["stock_valuation"]
        for vals in vals_list:
            if vals.get("account_id") != valuation_account.id:
                vals["analytic_distribution"] = distribution
        return vals_list

    # ------------------------------------------------------------------
    # Mandatory plan enforcement
    # ------------------------------------------------------------------
    def _analytic_distribution_validation_needed(self):
        """Whether the mandatory-plan check applies to this move.

        Return moves are kept out of scope: their applicability usually depends
        on the original move, so we treat them as optional to avoid blocking
        legitimate returns.
        """
        self.ensure_one()
        if self._is_in() and self._is_returned(valued_type="in"):
            return False
        if self._is_out() and self._is_returned(valued_type="out"):
            return False
        if self.company_id.anglo_saxon_accounting and self._is_dropshipped_returned():
            return False
        return True

    def _check_mandatory_analytic_distribution(self):
        """Raise a helpful error if a mandatory plan is not fully distributed."""
        self.ensure_one()
        relevant_plans = (
            self.env["account.analytic.plan"]
            .sudo()
            .with_company(self.company_id)
            .get_relevant_plans(
                product=self.product_id.id,
                picking_type=self.picking_type_id.id,
                business_domain="stock_move",
                company_id=self.company_id.id,
            )
        )
        mandatory_plan_ids = [
            plan["id"]
            for plan in relevant_plans
            if plan["applicability"] == "mandatory"
        ]
        if not mandatory_plan_ids:
            return
        precision = self.env["decimal.precision"].precision_get(
            "Percentage Analytic"
        )
        distribution_by_plan = defaultdict(float)
        for account_ids, percentage in (self.analytic_distribution or {}).items():
            accounts = self.env["account.analytic.account"].browse(
                int(account_id) for account_id in account_ids.split(",")
            )
            for account in accounts.exists():
                distribution_by_plan[account.root_plan_id.id] += percentage
        for plan_id in mandatory_plan_ids:
            if (
                float_compare(
                    distribution_by_plan.get(plan_id, 0.0),
                    100.0,
                    precision_digits=precision,
                )
                != 0
            ):
                raise ValidationError(
                    _(
                        "Product “%(product)s” requires a 100%% analytic "
                        "distribution on a mandatory plan before this transfer "
                        "can be validated.",
                        product=self.product_id.display_name,
                    )
                )

    def _action_done(self, cancel_backorder=False):
        if self.env.context.get("validate_analytic"):
            for move in self:
                if move._analytic_distribution_validation_needed():
                    move._check_mandatory_analytic_distribution()
        return super()._action_done(cancel_backorder=cancel_backorder)

    # ------------------------------------------------------------------
    # Reporting: enable group-by analytic account on stock moves
    # ------------------------------------------------------------------
    def _get_count_id(self, query):
        if query.table == self._table:
            return SQL("id")
        return super()._get_count_id(query)
