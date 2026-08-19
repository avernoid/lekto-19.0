from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    stock_move_date_adjust_max_days = fields.Integer(
        string="Maximum Movement Date Shift",
        default=0,
        help="Largest gap, in days, between a movement's current date and the date "
             "a regularisation may give it. Zero means no limit.",
    )
