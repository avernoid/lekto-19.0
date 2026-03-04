from datetime import datetime, time
from odoo import models, fields, api


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    hr_allocation_ids = fields.Many2many(
        comodel_name='hr.leave.allocation',
        string='Allocations',
        help='Shows the leave allocations related to this payslip for the specified period.',
        compute='compute_hr_allocation_leave_ids'
    )
    leave_ids = fields.Many2many(
        comodel_name='hr.leave',
        string='Leaves',
        help='Shows the leaves taken during the period of this payslip.',
        compute='compute_hr_allocation_leave_ids'
    )

    @api.depends('date_from', 'date_to', 'version_id')
    def compute_hr_allocation_leave_ids(self):
        for rec in self:
            allocations = []
            leaves = []
            if rec.date_from and rec.date_to and rec.version_id and rec.version_id.resource_calendar_id:
                day_from = datetime.combine(fields.Date.from_string(rec.date_from), time.min)
                day_to = datetime.combine(fields.Date.from_string(rec.date_to), time.max)
                calendar = rec.version_id.resource_calendar_id
                day_leave_intervals = rec.version_id.employee_id.list_leaves(day_from, day_to, calendar=calendar)
                for day, hours, leave in day_leave_intervals:
                    holidays = leave.holiday_id
                    if holidays:
                        for holiday in holidays:
                            leaves.append(holiday.id)
                            allocation = holiday.hr_leave_id
                            if allocation:
                                allocations.append(allocation.id)
            rec.hr_allocation_ids = list(set(allocations))
            rec.leave_ids = list(set(leaves))
