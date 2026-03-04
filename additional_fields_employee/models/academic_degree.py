
from odoo import fields, models


class AcademicDegree(models.Model):
    _name = 'academic.degree'
    _description = 'Academic Degree'

    code = fields.Char(
        string='Code',
        help='Official SUNAT code for this academic degree level. '
             'Used in electronic payroll declarations (T-Registro, PLAME).'
    )
    academic_description = fields.Char(
        string='Description',
        help='Full descriptive name of the academic degree level '
             '(e.g., "Complete University", "Technical Institute").'
    )
    name = fields.Char(
        string='Abbreviation',
        help='Short code or abbreviation displayed in dropdowns and reports.'
    )
