from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    exceeds_1500_uit = fields.Boolean(
        string='Exceeds 1500 UIT',
        help='Enable this if the company\'s annual income exceeds 1500 UIT (Unidades Impositivas Tributarias). '
             'This flag affects specific fields in the SIRE purchase reports as required by SUNAT regulations.',
    )