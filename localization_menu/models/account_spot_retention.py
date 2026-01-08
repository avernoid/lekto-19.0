from odoo import fields, models

class AccountSpotRetention(models.Model):
    _name = 'account.spot.retention'
    _description = 'SPOT Retention'

    name = fields.Char(
        string='Name',
        required=True,
        help='Name or description of the SPOT retention type. This identifies the specific classification for retention purposes.'
    )

