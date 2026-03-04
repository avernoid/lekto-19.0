from odoo import fields, models


class WorkOccupation(models.Model):
    _name = 'work.occupation'
    _description = 'Work Occupation'

    code = fields.Char(
        string='Code',
        help='Official SUNAT code for this work occupation category. '
             'Used in T-Registro and PLAME declarations.'
    )
    name = fields.Char(
        string='Name',
        help='Descriptive name of the occupation category.'
    )
    executive = fields.Boolean(
        string='Executive',
        help='Enable if this occupation category classifies the employee as an Executive. '
             'Affects CTS calculation and benefit thresholds.'
    )
    employee = fields.Boolean(
        string='Employee',
        help='Enable if this occupation category classifies the worker as an Employee (white-collar). '
             'Affects CTS calculation and benefit thresholds.'
    )
    worker = fields.Boolean(
        string='Worker',
        help='Enable if this occupation category classifies the worker as a Worker (blue-collar/obrero). '
             'Affects CTS calculation and benefit thresholds.'
    )
