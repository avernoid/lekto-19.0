from odoo import fields, models

class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    unpaid = fields.Boolean(
        string='Is Unpaid?',
        related='work_entry_type_id.unpaid',
        help='Indicates if the related work entry type is unpaid.'
    )
    is_social_benefits_license = fields.Boolean(
        string='Is License for Social Benefits?',
        related='work_entry_type_id.is_social_benefits_license',
        help='Indicates if this worked day record is a license that affects benefits.'
    )
    is_benefits_license_absence = fields.Boolean(
        string='Is Absence for Social Benefits?',
        related='work_entry_type_id.is_benefits_license_absence',
        help='Indicates if this worked day record is an absence affecting social benefits.'
    )
    is_calc_own_rule = fields.Boolean(
        string='Is calculated by its own rule?',
        related='work_entry_type_id.is_calc_own_rule',
        help='Indicates if this worked day line is calculated by its own specific rule.'
    )