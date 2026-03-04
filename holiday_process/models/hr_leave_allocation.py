import logging

from odoo import api, fields, models
from odoo.tools import format_date
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    to_date = fields.Date(
        string='To Date',
        help='End date of the vacation period covered by this allocation. '
             'Used to define the calculation range for proportional vacation days.',
    )
    from_date = fields.Date(
        string='From Date',
        help='Start date of the vacation period covered by this allocation. '
             'Together with "To Date", defines the period for which vacation days are computed.',
    )
    deadline = fields.Date(
        string='Enjoyment Deadline',
        help='Latest date by which the employee must use (enjoy) the vacation days in this allocation. '
             'Days not used before this date may be subject to payment or forfeiture according to company policy.',
    )
    is_holiday = fields.Boolean(
        string='Is Vacation?',
        help='Automatically set to True when the leave type assigned to this allocation corresponds to the '
             'standard vacation leave type (holiday_process.hr_leave_type_23). '
             'This flag enables vacation-specific workflows such as creating absence records.',
        compute='_compute_is_holiday',
        store=True
    )
    absence_ids = fields.One2many(
        comodel_name='hr.leave',
        inverse_name='hr_leave_id',
        string='Absences',
        help='List of leave (absence) records generated from this allocation. '
             'Each record represents a specific vacation period enjoyed or paid to the employee. '
             'An allocation with linked absences cannot be deleted — cancel absences first.',
    )
    payment_ids = fields.One2many(
        comodel_name='hr.leave.payment',
        inverse_name='allocation_id',
        string='Pagos Sin Goce',
        help='Vacation days that were paid to the employee without physical absence. '
             'These days are counted in "Vacations Taken or Paid" and reduce the pending balance.',
    )
    computed_holiday = fields.Float(
        string='Computed Vacations',
        help='Total vacation days earned under this allocation, based on accrual rules and the number_of_days_display field. '
             'Automatically recalculated when the allocation state or accrual records change.',
        compute='compute_days_holiday',
        store=True
    )
    used_holiday = fields.Float(
        string='Vacations Taken or Paid',
        help='Total vacation days already consumed via linked absence records (enjoyed or compensated). '
             'Only absences in a non-refused, non-cancelled state are counted. '
             'This value is subtracted from Computed Vacations to determine the Pending balance.',
        compute='compute_days_holiday',
        store=True
    )
    pending_holiday = fields.Float(
        string='Pending Vacations',
        help='Remaining vacation days available for this allocation (Computed Vacations minus Vacations Taken or Paid). '
             'A positive value means the employee still has days to enjoy or request. '
             'A value of zero or negative indicates the full allocation has been used.',
        compute='compute_days_holiday',
        store=True
    )

    def _compute_display_name(self):
        if self.env.context.get('show_holiday_summary'):
            for rec in self:
                date_from = format_date(self.env, rec.from_date) if rec.from_date else '—'
                rec.display_name = (
                    f"{rec.holiday_status_id.name or '?'}"
                    f" | {date_from}"
                    f" | {rec.pending_holiday:.1f} días"
                )
        else:
            super()._compute_display_name()

    def _recalculate_days(self):
        total_days = 0
        for rec in self.accruement_ids:
            total_days += rec.days_accrued
        self.computed_holiday = total_days - self.used_holiday
        self.pending_holiday = self.computed_holiday

    @api.depends('number_of_days_display', 'absence_ids', 'absence_ids.state', 'payment_ids', 'payment_ids.number_of_days', 'state')
    def compute_days_holiday(self):
        for rec in self:
            if rec.state in ('refuse', 'cancel'):
                rec.computed_holiday = 0.0
                rec.used_holiday = 0.0
                rec.pending_holiday = 0.0
                continue

            rec.computed_holiday = rec.number_of_days_display

            days_absent = sum(
                line.number_of_days
                for line in rec.absence_ids
                if line.state not in ('refuse', 'cancel')
            )
            days_paid = sum(line.number_of_days for line in rec.payment_ids)
            rec.used_holiday = days_absent + days_paid

            rec.pending_holiday = rec.computed_holiday - rec.used_holiday

    @api.depends('holiday_status_id')
    def _compute_is_holiday(self):
        holiday_id = self.env.ref('holiday_process.hr_leave_type_23', False)
        if holiday_id:
            for rec in self:
                if rec.holiday_status_id and rec.holiday_status_id == holiday_id:
                    rec.is_holiday = True

    def unlink(self):
        for rec in self:
            if rec.absence_ids:
                raise ValidationError('You must first delete or cancel all related absences before deleting this allocation.')
        return super(HrLeaveAllocation, self).unlink()

    def action_create_absence_holiday(self):
        holiday_id = self.env.ref('holiday_process.hr_leave_type_23')
        for rec in self:
            if rec.state == 'validate' or rec.state == 'validate1' and rec.holiday_status_id == holiday_id and \
                    rec.pending_holiday > 0:
                try:
                    self.env['hr.leave'].create({
                        'holiday_status_id': rec.holiday_status_id.id,
                        'employee_id': rec.employee_id.id,
                        'hr_leave_id': rec.id
                    })
                except Exception as e:
                    _logger.warning(e)
                    continue