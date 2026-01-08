from odoo import models, fields


class AccountAccount(models.Model):
    _inherit = 'account.account'

    # [V19 Migration] Field retained as is.
    adjustment_rate = fields.Float(
        string='Closing Exchange Rate',
        digits=(12, 6),
        help="Exchange rate used for the unrealized gain/loss calculation at the end of the period."
    )
