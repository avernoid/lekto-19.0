from collections import defaultdict
from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    has_holidays = fields.Boolean(
        string='Has Vacations',
        help='Indicates whether this employee is entitled to receive vacation allocations. '
             'When enabled, the employee will be included in mass vacation generation processes.',
        groups="hr.group_hr_user"
    )
    holidays_per_year = fields.Char(
        string='Vacation Days per Year',
        help='Number of vacation days the employee is entitled to per year based on their contract or internal policy. '
             'This value is used as a reference for salary rule calculations and is not directly editable from the UI.',
        groups="hr.group_hr_user"
    )
    additional_days = fields.Char(
        string='Additional Days',
        help='Extra vacation days granted to the employee beyond the standard annual entitlement. '
             'These may be assigned due to seniority, special agreements, or labor law provisions.',
        groups="hr.group_hr_user"
    )
    hr_allocation_ids = fields.One2many(
        comodel_name='hr.leave.allocation',
        inverse_name='employee_id',
        string='Vacation Lines',
        help='List of all leave allocation records linked to this employee. '
             'Each line shows the earned, taken, and pending vacation days for a specific period or allocation. '
             'Generated automatically via the Holiday Generator Wizard.',
        groups="hr.group_hr_user"
    )
    vacation_start_date = fields.Date(
        string='Start Vacation',
        help='The date from which vacation periods will be managed in Odoo for this employee. '
             'This is NOT the employee\'s employment start date, but rather the date from which '
             'the Holiday Generator Wizard will begin creating vacation allocations. '
             'Useful when migrating from another system and you only want to manage periods from a specific date forward.',
        groups="hr.group_hr_user"
    )

    def _get_work_days_data_batch_all(self, from_datetime, to_datetime, calendar=None):
        """
        Devuelve un diccionario con los días de trabajo de cada empleado entre
        from_datetime y to_datetime, usando su calendario asignado.
        """

        result = {}

        if isinstance(from_datetime, str):
            from_datetime = fields.Datetime.to_datetime(from_datetime)
        if isinstance(to_datetime, str):
            to_datetime = fields.Datetime.to_datetime(to_datetime)

        mapped_calendars = defaultdict(list)
        for employee in self:
            mapped_calendars[calendar or employee.resource_calendar_id].append(employee)

        for cal, employees in mapped_calendars.items():
            day_total = cal.with_context(holiday_status_id=True)._get_resources_day_total(
                from_datetime, to_datetime
            )
            intervals = cal.with_context(holiday_status_id=True)._attendance_intervals_batch(
                from_datetime, to_datetime
            )

            for employee in employees:
                resource_id = employee.resource_id.id
                if resource_id in intervals and resource_id in day_total:
                    result[employee.id] = cal._get_days_data(
                        intervals[resource_id], day_total[resource_id]
                    )
                else:
                    result[employee.id] = {}

        return result

    def action_open_holiday_generator(self):
        action = self.env.ref('holiday_process.action_holiday_generator_wizard').read()[0]
        action['context'] = {
            'default_employees_ids': self.ids,
            'from_employee_id': self.id,
        }
        return action

