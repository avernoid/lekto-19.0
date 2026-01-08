from odoo import fields, models

class AccountSpotDetraction(models.Model):
    _name = 'account.spot.detraction'
    _description = 'SPOT Detraction'

    name = fields.Char(
        string='Name',
        required=True,
        help='Name or description of the SPOT detraction type. This identifies the specific classification for detraction purposes.'
    )
