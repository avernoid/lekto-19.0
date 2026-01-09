from odoo import fields, models


class AccountSpotDetraction(models.Model):
    _inherit = 'account.spot.detraction'

    code = fields.Char(
        string='Code',
        required=True,
        default='00',
        help='Unique code required by SUNAT for this detraction type.'
    )
    rate = fields.Float(
        string="Rate %",
        required=True,
        default=0.0,
        help='Percentage rate applicable for this detraction.'
    )
