from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Openclaw connector credentials stored as ir.config_parameter sysconfs."""
    _inherit = 'res.config.settings'

    openclaw_api_url = fields.Char(
        string='Openclaw API URL',
        config_parameter='openclaw_connector.api_url',
        help='Base URL of the Openclaw API endpoint (e.g. https://api.openclaw.io). '
             'This is the root URL that all API requests will be sent to. '
             'Do not include trailing slashes or specific endpoint paths.',
    )
    openclaw_api_key = fields.Char(
        string='Openclaw API Key',
        config_parameter='openclaw_connector.api_key',
        help='Secret key used to authenticate requests with the Openclaw API. '
             'You can obtain this key from your Openclaw account dashboard '
             'under the API settings section. Keep this value confidential.',
    )
