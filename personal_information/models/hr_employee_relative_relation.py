from odoo import fields, models


class HrEmployeeRelativeRelation(models.Model):
    _name = 'hr.employee.relative.relation'
    _description = 'HR Employee Relative Relation'

    name = fields.Char(
        string='Parentesco',
        required=True,
        translate=True
    )
