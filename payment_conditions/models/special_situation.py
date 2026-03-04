from odoo import fields, models


class SpecialSituation(models.Model):
    _name = 'special.situation'
    _description = 'Special Situation'

    code = fields.Char(
        string='Code',
        help="Short identifier for this special situation (e.g., DIS for Disability, MAT for Maternity). "
             "Used in legal reports and payroll exports according to Peruvian labor regulations."
    )
    situation_description = fields.Char(
        string='Description',
        help="Full descriptive name of the special employment situation (e.g., 'Maternity Leave', 'Disability'). "
             "This text is shown in configuration menus and contract forms."
    )
    name = fields.Char(
        string='Abbreviation',
        help="Short abbreviation displayed in selectors, contract forms, and employee profiles (e.g., DIS, MAT, MIC). "
             "This is the value visible to HR Managers when classifying an employee's employment situation."
    )
