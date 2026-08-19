from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    stock_move_date_adjust_max_days = fields.Integer(
        related="company_id.stock_move_date_adjust_max_days",
        readonly=False,
    )
