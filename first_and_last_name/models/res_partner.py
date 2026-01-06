from odoo import models, fields


class Partner(models.Model):
    _inherit = 'res.partner'

    partner_name = fields.Char(
        string='First Name',
        help="The contact's individual first name(s)."
    )
    first_name = fields.Char(
        string='Paternal Surname',
        help="The contact's paternal last name."
    )
    second_name = fields.Char(
        string='Maternal Surname',
        help="The contact's maternal last name."
    )
