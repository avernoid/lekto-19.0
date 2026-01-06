from odoo import models, fields

class AccountAnalyticDistributionModel(models.Model):
    _inherit = 'account.analytic.distribution.model'

    pos_config_id = fields.Many2one(
        comodel_name='pos.config',
        string='Point of Sale',
        ondelete='cascade',
        help="Select specific Point of Sale Configuration. "
             "If set, this rule will only apply to orders generated from this specific Point of Sale. "
             "Useful for distinguishing sales performance or costs between different physical store locations or POS terminals."
    )
