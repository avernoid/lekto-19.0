from odoo import fields, models


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    show_in_time_off_request = fields.Boolean(
        string='Show Allocation in Time Off Request',
        default=False,
        help='When enabled, the system will display a related allocation selector on the Time Off request form. '\
             'Use this for leave types that require linking each absence to a specific vacation allocation '\
             '(e.g., Descanso Vacacional). When disabled, no allocation selector is shown and the '\
             'absence is recorded independently.'
    )
