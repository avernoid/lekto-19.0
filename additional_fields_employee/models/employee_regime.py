from odoo import fields, models


class EmployeeRegime(models.Model):
    _name = 'employee.regime'
    _description = 'Labor Regime'

    code = fields.Char(
        string='Code',
        help='Official SUNAT code for this labor regime. '
             'Used in T-Registro and PLAME declarations.'
    )
    regime_description = fields.Char(
        string='Description',
        help='Full descriptive name of the labor regime '
             '(e.g., "General Private Regime", "Public Sector D.L. 276").'
    )
    name = fields.Char(
        string='Abbreviation',
        help='Short code or abbreviation displayed in dropdowns and reports.'
    )
    private_sector = fields.Boolean(
        string='Private Sector',
        help='Enable if this regime applies to private sector employers.'
    )
    public_sector = fields.Boolean(
        string='Public Sector',
        help='Enable if this regime applies to public sector entities.'
    )
    other_entities = fields.Boolean(
        string='Other Entities',
        help='Enable if this regime applies to special entities '
             '(e.g., international organizations, NGOs).'
    )
    is_mype = fields.Boolean(
        string='Is MYPE?',
        help='Enable if this regime corresponds to a Micro or Small Enterprise (MYPE). '
             'MYPE regimes have reduced labor benefits and contribution rates.'
    )
