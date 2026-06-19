# Copyright 2026 Ganemo
# License OPL-1 (Odoo Proprietary License v1.0) - See LICENSE file.
from odoo import fields, models


class StockScrap(models.Model):
    _name = "stock.scrap"
    _inherit = ["stock.scrap", "analytic.mixin"]

    analytic_distribution = fields.Json(copy=False)

    def _prepare_move_values(self):
        vals = super()._prepare_move_values()
        if self.analytic_distribution:
            vals["analytic_distribution"] = self.analytic_distribution
        return vals

    def action_validate(self):
        return super(
            StockScrap, self.with_context(validate_analytic=True)
        ).action_validate()
