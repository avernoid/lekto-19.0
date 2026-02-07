from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    detraction_id = fields.Many2one(
        comodel_name='account.spot.detraction',
        string='Detraction Type',
        help='Select the Detraction type applicable to this invoice.'
    )
    retention_id = fields.Many2one(
        comodel_name='account.spot.retention',
        string='Retention',
        help='Select the Retention type applicable to this invoice.'
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
