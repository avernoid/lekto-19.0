# Copyright 2026 Ganemo
# License OPL-1 (Odoo Proprietary License v1.0) - See LICENSE file.
from odoo import models


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _get_custom_move_fields(self):
        # Make the distribution survive when a rule generates a chained move.
        return super()._get_custom_move_fields() + ["analytic_distribution"]
