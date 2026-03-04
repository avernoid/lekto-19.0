import logging
from datetime import datetime

import pytz
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


def _convert_date_timezone_to_utc(user, date_order, format_time='%Y-%m-%d %H:%M:%S'):
    tz = pytz.timezone(user.tz) if user.tz else pytz.utc
    date_order = datetime.strptime(date_order, format_time)
    datetime_with_tz = tz.localize(date_order, is_dst=None)
    date_order = datetime_with_tz.astimezone(pytz.utc)
    date_order = datetime.strftime(date_order, format_time)
    return date_order


class HolidaysGeneratorWizard(models.TransientModel):
    _name = 'holiday.generator.wizard'
    _description = 'Vacation Generator'

    employees_ids = fields.Many2many(
        comodel_name='hr.employee',
        string='Employees',
        help='Select the specific employees for whom vacation allocations will be generated. '
             'If left empty, the system will automatically process all active employees who have '
             '"Has Vacations" enabled and a Service Start Date defined.'
    )
    is_generated = fields.Boolean(
        string='Was Generated?',
        help='Internal flag set to True after vacation allocations have been generated. '
             'Controls the read-only state of the employee list and hides the action buttons.'
    )
    set_period = fields.Boolean(
        string='Define Period',
        help='When enabled, allows you to restrict the generation to a specific range of years. '
             'Only accrual periods whose start year falls within the defined date range will be created. '
             'When disabled, all periods from the employee\'s service start date through the current year are generated.'
    )
    date_from = fields.Date(
        string='From',
        help='Start of the year range to include in vacation generation. '
             'Only accrual periods starting on or after this year will be created. '
             'Requires "Define Period" to be enabled.'
    )
    date_to = fields.Date(
        string='To',
        help='End of the year range to include in vacation generation. '
             'Only accrual periods starting before or on this year will be created. '
             'Requires "Define Period" to be enabled.'
    )

    @api.onchange('set_period')
    def onchange_set_period(self):
        self.date_from = self.date_to = False

    def action_generate_holidays(self):
        if self.employees_ids:
            employees = self.employees_ids
        else:
            employees = self.env['hr.employee'].search([
                ('has_holidays', '=', True),
                ('vacation_start_date', '!=', False)
            ])
        arr_employee = []
        for employee in employees:
            start_date = employee.vacation_start_date
            if not start_date:
                continue
            end_tdate = employee.service_termination_date
            arr_employee = self.set_period_holidays(employee, start_date, end_tdate, arr_employee)
        arr_employee = list(set(arr_employee))
        form = self.env.ref('holiday_process.holiday_generator_wizard_view_form')
        ctx = dict(self.env.context, default_is_generated=True, default_employees_ids=arr_employee)
        return {
            'name': 'Empleados con vacaciones generadas',
            'res_model': self._name,
            'view_mode': 'form',
            'views': [(form.id, 'form')],
            'context': ctx,
            'view_id': form.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def action_close_and_reload_employee(self):
        employee_id = self.env.context.get('from_employee_id')
        if employee_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'hr.employee',
                'res_id': employee_id,
                'view_mode': 'form',
                'views': [(False, 'form')],
                'target': 'current',
            }
        return {'type': 'ir.actions.act_window_close'}

    def set_period_holidays(self, employee, start_date, end_tdate, arr_employee):
        today = fields.Date.today()
        end_date = start_date + relativedelta(months=12) - relativedelta(days=1)
        start_date, end_date, arr_employee = self.generate_holidays(start_date, end_date, employee, arr_employee)

        if end_tdate:
            while start_date.year <= end_tdate.year:
                start_date, end_date, arr_employee = self.generate_holidays(start_date, end_date, employee, arr_employee)
        else:
            while end_date.year <= today.year or start_date.year <= today.year <= end_date.year:
                start_date, end_date, arr_employee = self.generate_holidays(start_date, end_date, employee, arr_employee)
        return arr_employee

    def generate_holidays(self, start_date, end_date, employee, arr_employee):
        years = [] if not self.set_period else list(range(self.date_from.year, self.date_to.year + 1))
        if start_date.year in years or not self.set_period:
            holiday_id = self.env.ref('holiday_process.hr_leave_type_23')
            accrual_plan_id = self.env.ref('holiday_process.hr_leave_accrual_plan_vacacional')
            rec = self.env['hr.leave.allocation'].search([
                ('from_date', '=', start_date),
                ('to_date', '=', end_date),
                ('holiday_status_id', '=', holiday_id.id),
                ('employee_id', '=', employee.id)
            ])
            if not rec:
                date_order_from = '{} 12:00:00'.format(start_date)
                date_order_to = '{} 12:00:00'.format(end_date)
                nro_days = int(employee.additional_days) + int(employee.holidays_per_year)
                today = fields.Date.today()
                is_past_period = end_date < today

                vals = {
                    'name': 'Vacaciones {} {}'.format(start_date, end_date),
                    'holiday_status_id': holiday_id.id,
                    'to_date': end_date,
                    'from_date': start_date,
                    'date_from': date_order_from,
                    'date_to': date_order_to,
                    'employee_id': employee.id,
                    'state': 'confirm',
                    'deadline': end_date + relativedelta(months=8),
                }

                if is_past_period:
                    # Período ya terminado: días exactos sin acumulación
                    vals.update({
                        'allocation_type': 'regular',
                        'number_of_days': nro_days,
                    })
                else:
                    # Período actual o futuro: acumulación mensual proporcional
                    vals.update({
                        'allocation_type': 'accrual',
                        'accrual_plan_id': accrual_plan_id.id,
                        'number_of_days': 0,
                        'unit_per_interval': 'days',
                        'number_per_interval': nro_days / 12,
                        'interval_number': 1,
                        'interval_unit': 'months',
                    })

                allocation_id = self.env['hr.leave.allocation'].create(vals)
                try:
                    allocation_id.state = 'validate'
                    if not is_past_period:
                        allocation_id._update_accrual_allocation()
                except Exception as e:
                    _logger.info('Vacación no aprobada:\n  .Empleado: {}\n  .Asignación:{}\n  .Error:{}'.format(employee.name, allocation_id.id, e))
                arr_employee.append(employee.id)
        start_date += relativedelta(months=12)
        end_date = start_date + relativedelta(months=12) - relativedelta(days=1)
        return start_date, end_date, arr_employee