# Copyright 2026 Ganemo
# License OPL-1 (Odoo Proprietary License v1.0) - See LICENSE file.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    cogs_analytic_exclude_valuation = fields.Boolean(
        related="company_id.cogs_analytic_exclude_valuation",
        readonly=False,
    )
