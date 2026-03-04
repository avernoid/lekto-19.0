from odoo import fields, models


class VariablePayment(models.Model):
    _name = 'variable.payment'
    _description = 'Variable Payment'

    code = fields.Char(
        string='Code',
        help="Short identifier for this variable remuneration category (e.g., COM for Commission, BON for Bonus). "
             "Used in reports and payroll exports to identify the variable pay scheme."
    )
    name = fields.Char(
        string='Abbreviation',
        help="Short abbreviation and display name for this variable payment type (e.g., COM, BON, INC). "
             "This is the value shown to HR Managers when classifying an employee's remuneration scheme."
    )
