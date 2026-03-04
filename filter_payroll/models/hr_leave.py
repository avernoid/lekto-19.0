from odoo import fields, models

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    unpaid = fields.Boolean(
        string='Is Unpaid',
        related='holiday_status_id.unpaid',
        help='Indicates if this leave is unpaid.'
    )
    is_social_benefits_license = fields.Boolean(
        string='Is License for Social Benefits?',
        related='holiday_status_id.is_social_benefits_license',
        help='Indicates if this leave is considered a license that affects social benefits (CTS, Gratifications).'
    )
    is_benefits_license_absence = fields.Boolean(
        string='Is Absence for Social Benefits?',
        related='holiday_status_id.is_benefits_license_absence',
        help='Indicates if this leave is considered an absence that affects calculations of social benefits.'
    )
    is_calc_own_rule = fields.Boolean(
        string='Is calculated by its own rule?',
        related='holiday_status_id.is_calc_own_rule',
        help='Indicates if this leave type is calculated with its own specific payroll calculation rule.'
    )
    code_holiday = fields.Char(
        string='Absence Code',
        related='holiday_status_id.code',
        help='Code of the specific absence or leave type linked to this record.'
    )