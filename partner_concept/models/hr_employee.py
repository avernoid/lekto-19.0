from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    partner_concept_ids = fields.Many2many(
        comodel_name='hr.partner.concept',
        relation='hr_employee_hr_partner_concept_rel',
        string='Salary Rules',
        help='Specific salary concepts and conditions applied to this employee. Use this to assign individualized values for deductions or allowances that are uniquely applicable here.',
        groups='hr.group_hr_user'
    )
