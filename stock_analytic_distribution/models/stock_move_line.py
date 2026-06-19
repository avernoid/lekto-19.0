# Copyright 2026 Ganemo
# License OPL-1 (Odoo Proprietary License v1.0) - See LICENSE file.
from odoo import fields, models
from odoo.tools import SQL


class StockMoveLine(models.Model):
    _name = "stock.move.line"
    _inherit = ["stock.move.line", "analytic.mixin"]

    analytic_distribution = fields.Json(copy=False)

    def write(self, vals):
        res = super().write(vals)
        if "analytic_distribution" in vals and not self.env.context.get(
            "skip_analytic_move_sync"
        ):
            # Editing the distribution on a detailed operation updates the move
            # so the value that gets posted stays in sync with what the user
            # sees. The reverse propagation is guarded to avoid a write loop.
            self.move_id.with_context(skip_analytic_move_line_sync=True).write(
                {"analytic_distribution": vals["analytic_distribution"]}
            )
        return res

    def _prepare_stock_move_vals(self):
        """A move line created on its own spawns a move; carry the distribution."""
        vals = super()._prepare_stock_move_vals()
        if self.analytic_distribution:
            vals["analytic_distribution"] = self.analytic_distribution
        return vals

    def _get_count_id(self, query):
        if query.table == self._table:
            return SQL("id")
        return super()._get_count_id(query)
