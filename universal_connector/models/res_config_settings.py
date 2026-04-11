from odoo import models


class ResConfigSettings(models.TransientModel):
    """Foundation for connector settings. Extended by each connector module."""
    _inherit = 'res.config.settings'
