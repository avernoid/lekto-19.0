from odoo import fields, models

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    is_social_benefits_license = fields.Boolean(
        string='Is License for Social Benefits?',
        related='holiday_status_id.is_social_benefits_license',
        help='Indicates if this attendance is considered a license that affects social benefits like CTS or Gratifications.'
    )
    is_benefits_license_absence = fields.Boolean(
        string='Is Absence for Social Benefits?',
        related='holiday_status_id.is_benefits_license_absence',
        help='Indicates if this attendance is considered an absence that affects social benefits computations.'
    )
    is_calc_own_rule = fields.Boolean(
        string='Is calculated by its own rule?',
        related='holiday_status_id.is_calc_own_rule',
        help='Indicates if this concept has a specific calculation rule in payroll.'
    )
    unpaid = fields.Boolean(
        string='Is Unpaid',
        related='holiday_status_id.unpaid',
        help='Indicates if this attendance is unpaid.'
    )
    code_holiday = fields.Char(
        string='Absence Code',
        related='holiday_status_id.code',
        help='Code of the specific absence or leave type linked to this attendance.'
    )
