from odoo import fields, models


class HealthRegime(models.Model):
    _name = 'health.regime'
    _description = 'Health Regime'

    code = fields.Char(
        string='Code',
        help='Official SUNAT code for this health regime. '
             'Used in T-Registro and PLAME declarations.'
    )
    health_description = fields.Char(
        string='Description',
        help='Full descriptive name of the health coverage type '
             '(e.g., "EsSalud Regular", "EPS Private").'
    )
    name = fields.Char(
        string='Abbreviation',
        help='Short code or abbreviation displayed in dropdowns and reports.'
    )
