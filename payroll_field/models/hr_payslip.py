from dateutil.relativedelta import relativedelta
from lxml import etree
from odoo import models, fields, api


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    employee_category_ids = fields.Many2many(
        comodel_name='hr.employee.category',
        string='Employee Tags',
        help='Tags assigned to the employee. Useful for filtering and '
             'grouping payslips by employee classification or category.',
        related='employee_id.category_ids'
    )
    date_start = fields.Char(
        string='Month/Year',
        help='Text representation of the payroll month in MM/YYYY format. '
             'Computed automatically from the payslip date range.',
        compute='_compute_date_start',
        store=True
    )
    date_start_dt = fields.Date(
        string='Payroll Month',
        help='Date field indicating which month the payslip corresponds to. '
             'When the payslip spans two months, the month with the most days '
             'is selected. Used for grouping and analysis by payroll period.',
        compute='_compute_date_start',
        store=True
    )
    month = fields.Char(
        string='Payroll Month Number',
        help='Two-digit month number (01-12) of the computed payroll month. '
             'Useful for sorting and filtering by month.',
        compute='_compute_date_start',
        store=True
    )
    year = fields.Char(
        string='Payroll Year',
        help='Four-digit year of the computed payroll month. '
             'Useful for sorting and filtering by year.',
        compute='_compute_date_start',
        store=True
    )

    @api.depends('date_from', 'date_to')
    def _compute_date_start(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                rec.date_start, rec.year, rec.month, rec.date_start_dt = self.generate_date_start_month_year(
                    rec.date_from, rec.date_to)

    def generate_date_start_month_year(self, date_from, date_to):
        if date_from.strftime('%m') != date_to.strftime('%m'):
            from_date = self.get_new_date(date_from, 31)
            from_days = self.number_days_per_range(from_date, date_from)

            to_date = self.get_new_date(date_to, 1)
            to_days = self.number_days_per_range(date_to, to_date)
            if from_days > to_days:
                name = date_from
            else:
                name = date_to
        else:
            name = date_to
        date_start = '{}/{}'.format(name.strftime('%m'), name.strftime('%Y'))
        year = name.strftime('%Y')
        month = name.strftime('%m')
        return date_start, year, month, name

    @staticmethod
    def number_days_per_range(start, end):
        return (start - end).days

    @staticmethod
    def get_new_date(date_from, days):
        return date_from + relativedelta(day=days)
    
    def _get_worked_day_lines_hours_per_day(self):
        for rec in self:
            calendar = rec.employee_id.resource_calendar_id
            return calendar.hours_per_day if calendar else 8.0 
