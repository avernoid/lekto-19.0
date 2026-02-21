from odoo import api, fields, models

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    eeff_ple_id = fields.Many2one(
        string='3.1 Rubro ESF',
        comodel_name='eeff.ple',
        related='account_id.eeff_ple_id',
        store=True
    )