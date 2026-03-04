from odoo import fields, models


class HolidaysUpdateWizard(models.TransientModel):
    _name = 'holiday.update.wizard'
    _description = 'Vacation Days Updater'

    date = fields.Date(
        string='Date',
        required=True,
        help='Reference date for the recalculation. Only accrual records with an accrual date '\
             'greater than or equal to this date will be updated with the new monthly interval. '\
             'Accrual records prior to this date will remain unchanged, preserving the historical data. '\
             'Set this to the date from which the new \"Vacation Days per Year\" value should take effect.'
    )

    def action_generate_holidays(self):
        self._recalculate_holidays_per_new_interval()

    def _recalculate_holidays_per_new_interval(self):
        self.ensure_one()

        hr_employees = self.env['hr.employee'].search([
            ('company_id', '=', self.env.company.id),
            ('current_version_id.active', '=', True),
            ('vacation_start_date', '!=', False),
        ])

        for employee in hr_employees:
            new_interval_holiday = round(float(employee.holidays_per_year) / 12, 2)

            for leave_allocation in employee.hr_allocation_ids:
                for day in leave_allocation.accruement_ids:
                    if day.accrued_on >= self.date:
                        day.days_accrued = new_interval_holiday

                leave_allocation._recalculate_days()
