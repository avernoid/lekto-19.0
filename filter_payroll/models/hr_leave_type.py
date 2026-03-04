from odoo import fields, models

class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    unpaid = fields.Boolean(
        related='work_entry_type_id.unpaid', 
        default=None,
        string='Is Unpaid',
        help='Indicates if this leave type is unpaid.'
    )
    is_social_benefits_license = fields.Boolean(
        string='Is License for Social Benefits?',
        related='work_entry_type_id.is_social_benefits_license',
        help='Indicates if this leave type is considered a license that affects social benefits.'
    )
    is_benefits_license_absence = fields.Boolean(
        string='Is Absence for Social Benefits?',
        related='work_entry_type_id.is_benefits_license_absence',
        help='Indicates if this leave type is considered an absence affecting social benefits.'
    )
    is_calc_own_rule = fields.Boolean(
        string='Is calculated by its own rule?',
        related='work_entry_type_id.is_calc_own_rule',
        help='Indicates if this leave type carries its own specific payroll calculation rule.'
    )
