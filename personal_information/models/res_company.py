from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    generate_legal_name = fields.Boolean(
        string='Auto-generate Legal Name',
        default=False,
        help='If checked, the Legal Name will be automatically generated from the Firstname and Lastnames.'
    )
