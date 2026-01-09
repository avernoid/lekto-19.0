from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    voucher_payment_date = fields.Date(
        related='move_id.voucher_payment_date',
        string='Payment Date',
        store=True,
        help='Date when the detraction payment was made.'
    )
    voucher_number = fields.Char(
        related='move_id.voucher_number',
        string='Voucher Number',
        store=True,
        help='Number of the payment voucher issued by the bank.'
    )