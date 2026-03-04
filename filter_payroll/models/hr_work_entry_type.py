from odoo import fields, models

class HrWorkEntryType(models.Model):
    _inherit = 'hr.work.entry.type'

    unpaid = fields.Boolean(
        string='Is Unpaid?',
        help='Mark this if the work entry type is an unpaid time off.'
    )
    is_social_benefits_license = fields.Boolean(
        string='Is License for Social Benefits?',
        help='Check if this type is a license affecting CTS or Gratification computations.'
    )
    is_benefits_license_absence = fields.Boolean(
        string='Is Absence for Social Benefits?',
        help='Check if this type is an absence affecting social benefits.'
    )