from odoo import fields, models


class TypeContract(models.Model):
    _name = 'type.contract'
    _description = 'Contract Type'

    code = fields.Char(
        string='Code',
        help='Official SUNAT code for this contract type. '
             'Used in T-Registro declarations.'
    )
    contract_type = fields.Char(
        string='Contract Type',
        help='Full descriptive name of the contract classification '
             '(e.g., "Indefinite", "Fixed-term", "Part-time").'
    )
    name = fields.Char(
        string='Abbreviation',
        help='Short code or abbreviation displayed in dropdowns and reports.'
    )
