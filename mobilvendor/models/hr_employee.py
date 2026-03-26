from odoo import fields, models

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    mobilvendor_code = fields.Char(string='Mobilvendor Code', copy=False, index=True)
    mobilvendor_assignment_ids = fields.One2many(
        'mobilvendor.route.employee',
        'employee_id',
        string='Route Assignments'
    )


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    mobilvendor_code = fields.Char(readonly=True)
    mobilvendor_assignment_ids = fields.One2many(
        'mobilvendor.route.employee',
        'employee_id',
        string='Route Assignments',
        readonly=True
    )