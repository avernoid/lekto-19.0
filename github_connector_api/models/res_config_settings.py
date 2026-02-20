from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    github_token = fields.Char(
        string='Github Token',
        config_parameter='github.access_token'
    )
