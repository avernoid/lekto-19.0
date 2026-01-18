from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    carrier_ref_number = fields.Char(
        string='Carrier Reference Number',
        help='Reference of the Carrier Guide associated with this invoice.'
    )
    aditional_document_reference = fields.Char(
        string='Additional Document Reference',
        help='Reference to any other related document (e.g. Manual Purchase Order).'
    )
