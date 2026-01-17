from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    generate_legal_name = fields.Boolean(
        related='company_id.generate_legal_name',
        readonly=False,
        string='Auto-generate Legal Name',
    )
