from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    annexed_establishment = fields.Char(
        string='Establishment Annex',
        default='0000',
        help='Code assigned by SUNAT for the establishment annex declared in the RUC. This code is mandatory for electronic invoicing and official books in Peru.'
    )
