from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    detraction_id = fields.Many2one(
        comodel_name='account.spot.detraction',
        string='Detraction',
        help='Select the Detraction type applicable to this invoice.'
    )
    retention_id = fields.Many2one(
        comodel_name='account.spot.retention',
        string='Retention',
        help='Select the Retention type applicable to this invoice.'
    )
    voucher_payment_date = fields.Date(
        string='Payment Date',
        help='Date when the detraction payment was made.'
    )
    voucher_number = fields.Char(
        string='Voucher Number',
        help='Number of the payment voucher issued by the bank.'
    )
    operation_type_detraction = fields.Selection(
        selection=[
            ('01', 'Sale of Goods or Services'),
            ('02', 'Withdrawal of Goods Taxed with IGV'),
            ('03', 'Transfer that is not a Sale'),
            ('04', 'Sale through Products Exchange'),
            ('05', 'Sale of Goods Exempt from IGV')
        ],
        string='Operation Type',
        help='Specify the type of operation for SPOT purposes.'
    )
