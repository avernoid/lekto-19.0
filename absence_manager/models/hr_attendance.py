from odoo import fields, models


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    leave_id = fields.Many2one(
        comodel_name='hr.leave',
        string='Leave',
        help="The leave request that generated this attendance record. "
             "This link is created automatically when a leave is approved with "
             "'Report in attendance?' enabled, or by the Absence Monitor CRON.",
    )
    holiday_status_id = fields.Many2one(
        comodel_name='hr.leave.type',
        string='Leave Type',
        help="The type of leave associated with this attendance record. "
             "This is set automatically and updated when the leave type changes "
             "on the linked leave request.",
        readonly=True,
    )