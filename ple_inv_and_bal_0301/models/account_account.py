from odoo import api, fields, models

class AccountAccount(models.Model):
    _inherit = 'account.account'

    eeff_ple_id = fields.Many2one(
        string='3.1 Rubro ESF',
        comodel_name='eeff.ple'
    )
    eeff_type = fields.Selection(
        string='Tipo EEFF PLE',
        related='eeff_ple_id.eeff_type'
    )