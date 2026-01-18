from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    carrier_ref_number = fields.Char('Guía(s) de Remisión')
    aditional_document_reference = fields.Char(string='Otro tipo de documento')
