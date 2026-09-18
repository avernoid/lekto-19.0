from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockLandedCost(models.Model):
    _inherit = "stock.landed.cost"

    variance_revaluation_ids = fields.One2many(
        "stock.value.revaluation", "landed_cost_id", string="Late Revaluations")
    variance_revaluation_count = fields.Integer(compute="_compute_variance_revaluation_count")

    @api.depends("variance_revaluation_ids")
    def _compute_variance_revaluation_count(self):
        for cost in self:
            cost.variance_revaluation_count = len(cost.variance_revaluation_ids)

    def button_validate(self):
        """Run the late revaluation engine around the native validation (design v4, D2).

        The snapshot must precede ``super()``: the native method rewrites the receipt values
        (``_get_value_from_extra``) and recomputes the product cost. The adjustment lines are computed
        first when missing, exactly as the native method does (stock_landed_cost.py:105-107).
        """
        if self.env.context.get("variance_skip_engine"):
            return super().button_validate()
        self.filtered(lambda c: not c.valuation_adjustment_lines).compute_landed_cost()
        Revaluation = self.env["stock.value.revaluation"]
        snapshots = {}
        for cost in self:
            for product in cost.valuation_adjustment_lines.move_id.product_id.filtered("is_storable"):
                snapshots[(cost.id, product.id)] = Revaluation._variance_snapshot(product, cost.company_id)
        res = super().button_validate()
        for cost in self:
            cost._variance_run_engine(snapshots)
        return res

    def _variance_run_engine(self, snapshots):
        self.ensure_one()
        Revaluation = self.env["stock.value.revaluation"]
        company = self.company_id
        for product in self.valuation_adjustment_lines.move_id.product_id.filtered("is_storable"):
            product = product.with_company(company)
            lines = self.valuation_adjustment_lines.filtered(lambda l, p=product: l.move_id.product_id == p)
            revaluation = sum(lines.mapped("additional_landed_cost"))
            valuation = product.product_tmpl_id.get_product_accounts()["stock_valuation"]
            native = sum(self.account_move_id.line_ids.filtered(
                lambda l, p=product: l.account_id == valuation and l.product_id == p).mapped("balance"))
            # Counterparts of what Odoo did not capitalise, per cost line account, pro rata: the native entry
            # capitalises every adjustment line of a product with the same remaining ratio.
            by_account = {}
            for line in lines:
                account = line.cost_line_id.account_id or line.cost_line_id.product_id._get_product_accounts()["expense"]
                by_account[account] = by_account.get(account, 0.0) + line.additional_landed_cost
            splits = [(account, (amount / revaluation) * (revaluation - native) if revaluation else 0.0)
                      for account, amount in by_account.items()]
            Revaluation._variance_handle_event(
                product, company, snapshots[(self.id, product.id)], self.date, "landed_cost", revaluation,
                native_amount=native, source_splits=splits, landed_cost_id=self.id)

    def compute_landed_cost(self):
        """Refuse to wipe the adjustment lines of a validated cost.

        The core method is public, RPC-callable and has no state guard, and it opens with an unlink of
        every line of the cost -- the evidence of every revaluation event recorded for it.
        """
        done = self.filtered(lambda c: c.state == "done")
        if done:
            raise UserError(_(
                "Cannot recompute a validated landed cost (%s).",
                ", ".join(done.mapped("name")),
            ))
        return super().compute_landed_cost()

    def action_view_variance_revaluations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window", "name": _("Late Revaluations"),
            "res_model": "stock.value.revaluation", "view_mode": "list,form",
            "domain": ["|", ("landed_cost_id", "=", self.id), ("parent_id.landed_cost_id", "=", self.id)],
        }
