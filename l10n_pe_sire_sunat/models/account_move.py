from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_pe_is_complement_sire = fields.Boolean(
        string='SIRE Complement',
        help='Enable this field if the invoice is a physical CPE (Comprobante de Pago Electrónico) '
             'that needs to be included in the SIRE complement TXT file. When activated, '
             'the record will be picked up by the complement report generator.',
    )
