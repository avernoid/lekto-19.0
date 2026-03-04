from odoo import api, fields, models


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    hr_leave_id = fields.Many2one(
        comodel_name='hr.leave.allocation',
        string='Allocation',
        help='The vacation allocation record this absence is linked to. '
             'When set, the days consumed by this absence are deducted from the pending balance of the allocation. '
             'Required for vacation sale/purchase petitions generated via the Holiday Process module.',
    )
    show_in_time_off_request = fields.Boolean(
        related='holiday_status_id.show_in_time_off_request',
        string='Show Allocation in Time Off Request',
    )
    from_date = fields.Date(
        string='From Date',
        help='Start date of the absence period. Used to define the date range for this specific leave request.',
    )
    from_to = fields.Date(
        string='To Date',
        help='End date of the absence period. Together with "From Date", defines the full duration of this leave request.',
    )

    @api.onchange('holiday_status_id')
    def onchange_holiday_status_id(self):
        if self.holiday_status_id and self.holiday_status_id.show_in_time_off_request:
            self.hr_leave_id = False

