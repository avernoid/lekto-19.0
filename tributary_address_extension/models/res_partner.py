from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    annexed_establishment = fields.Char(
        string='Establecimiento anexo',
        default='0000',
        help='Código asignado por SUNAT para el establecimiento anexo declarado en el RUC.'
    )
