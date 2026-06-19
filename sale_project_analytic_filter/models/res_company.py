# Copyright 2026 Ganemo
# License OPL-1 (Odoo Proprietary License v1.0) - See LICENSE file.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    cogs_analytic_exclude_valuation = fields.Boolean(
        string="Keep analytic off the COGS stock valuation line",
        default=True,
        help="When enabled, the analytic distribution of Cost of Goods Sold "
        "journal items is cleared on the line booked on the product's stock "
        "valuation account (the inventory counterpart of the COGS pair), while "
        "the COGS expense line keeps it. This prevents the two COGS lines from "
        "cancelling each other out in the analytic ledger, and applies the same "
        "criterion the inventory valuation entry uses. Disable to fall back to "
        "the standard behaviour.",
    )
