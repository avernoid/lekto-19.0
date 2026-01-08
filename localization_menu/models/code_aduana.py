from odoo import fields, models

class CodeAduana(models.Model):
    _name = 'code.aduana'
    _description = 'Customs Unit Code (Customs)'

    name = fields.Char(
        string='Description',
        required=True,
        help='Descriptive name of the Customs Unit. This helps identify the specific customs location or entity.'
    )
    code = fields.Char(
        string='Code',
        required=True,
        help='Unique code identifier for the Customs Unit (e.g., 001, 118). Use the official code assigned by the customs authority.'
    )