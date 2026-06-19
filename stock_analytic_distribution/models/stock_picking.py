# Copyright 2026 Ganemo
# License OPL-1 (Odoo Proprietary License v1.0) - See LICENSE file.
from odoo import api, fields, models


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "analytic.mixin"]

    analytic_distribution = fields.Json(
        copy=False,
        help="Analytic distribution applied to this whole transfer. It is a "
        "convenience default: setting it here autocompletes the analytic "
        "distribution of every move of the transfer, so you can configure it "
        "once for all the lines. Each move can still keep its own distribution, "
        "and any value set on a line is respected when the transfer is "
        "validated. Changing this header value re-applies it to all the moves of "
        "the transfer, overwriting the per-line values, the same way the source "
        "and destination locations cascade to the moves. For products with "
        "automated (real time) valuation, the distribution of each move is "
        "posted on the counterpart line of its inventory valuation journal entry."
    )

    @api.onchange("analytic_distribution")
    def _onchange_analytic_distribution(self):
        """Use the transfer distribution to autocomplete its moves.

        Works like the source/destination locations: setting it on the header
        fills the lines, but each move stays free to keep its own value.
        """
        if self.analytic_distribution:
            self.move_ids.analytic_distribution = self.analytic_distribution

    def button_validate(self):
        # Flag the validation so mandatory analytic plans are enforced on the
        # moves through ``_action_done``.
        return super(
            StockPicking, self.with_context(validate_analytic=True)
        ).button_validate()
