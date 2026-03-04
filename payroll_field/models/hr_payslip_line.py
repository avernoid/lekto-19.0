from dateutil.relativedelta import relativedelta
from lxml import etree
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    date_start = fields.Char(
        string='Month/Year',
        help='Text representation (MM/YYYY) of the payroll month.',
        related="slip_id.date_start"
    )
    date_start_dt = fields.Date(
        string='Payroll Month',
        help='Computed payroll month date. Used for analysis grouping by period.',
        related="slip_id.date_start_dt",
        store=True
    )
    state = fields.Selection(
        string='Status',
        help='Current status of the payslip (Draft, Waiting, Done, etc.).',
        related="slip_id.state",
    )
    department_id = fields.Many2one(
        comodel_name='hr.department',
        string='Department',
        help='Department of the employee, used for filtering and grouping.',
        related='employee_id.department_id',
    )
    disability = fields.Boolean(
        string='Disability',
        help='Whether the employee has a registered disability.',
        related='employee_id.disability',
    )
    struct_id = fields.Many2one(
        comodel_name='hr.payroll.structure',
        string='Structure',
        help='Payroll structure used for this payslip.',
        related='slip_id.struct_id',
    )
    name = fields.Char(
        string='Name',
        help='Name of the salary rule applied to this payslip line.',
        related='salary_rule_id.name'
    )
    code = fields.Char(
        string='Code',
        help='Code of the salary rule applied to this payslip line.',
        related='salary_rule_id.code'
    )
    report_category_id = fields.Many2one(
        comodel_name='hr.salary.rule.report.category',
        string='Report Category',
        related='salary_rule_id.report_category_id',
        store=True,
    )
    parent_report_category_id = fields.Many2one(
        comodel_name='hr.salary.rule.report.category',
        string='Parent Report Category',
        related='report_category_id.parent_id',
        store=True,
    )
    payslip_run_id = fields.Many2one(
        comodel_name='hr.payslip.run',
        string='Pay Run',
        help='Batch or Pay Run to which this payslip line belongs.',
        related='slip_id.payslip_run_id',
        store=True,
    )
    
    def set_filter_six_month_before(self, arch):
        for node in arch.xpath("//filter[@name='six_month_before']"):
            date_now = fields.Date.today()
            hr_payslip = self.env['hr.payslip']
            hr_payslip_line = self.env['hr.payslip.line']
            date_start, year, month, _ = hr_payslip.generate_date_start_month_year(date_now, date_now)
            month = int(month)
            year = int(year)
            start_m, star_y = hr_payslip_line._get_month(year, month, 6)
            end_m, end_y = hr_payslip_line._get_month(year, month, 1)
            periods = hr_payslip_line._get_periods(start_m, star_y, end_m, end_y)
            modifiers = "[('date_start', 'in', {})]"
            modifiers = modifiers.format(periods)
            node.set('domain', modifiers)
        return arch

    @staticmethod
    def _get_periods(start_m, start_y, end_m, end_y):
        """
        :param start_m: Initial month of period
        :param start_y: Initial year of period
        :param end_m: Final month of period
        :param end_y: Final year of period
        :return: Return list of months between 'start_m/star_y' and 'end_m/end_y' => Ex: 08/18 12/18 = [08/18, 09/18, 10/18, 11/18, 12/18]
        """
        start = '{}/{}'.format("{:02d}".format(start_m), start_y)
        end = '{}/{}'.format("{:02d}".format(end_m), end_y)
        periods = [start]
        value = False
        if start == end:
            return periods
        while value != end:
            if start_y == end_y:
                start_m += 1
            else:
                start_m += 1
                if start_m == 13:
                    start_y += 1
                    start_m = 1
            value = '{}/{}'.format("{:02d}".format(start_m), start_y)
            periods.append(value)
        return periods

    @staticmethod
    def _get_month(year, month, value_month):
        value = month - value_month
        if value < 0:
            new_month = 12 + value
            new_year = year - 1
        elif value == 0:
            new_month = 12
            new_year = year - 1
        else:
            new_month = value
            new_year = year
        return new_month, new_year
    
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super(HrPayslipLine, self)._get_view(view_id, view_type, **options)
        hr_payslip = self.env['hr.payslip.line']
        if view_type in ('search'):
            arch = self.set_filter_six_month_before(arch)
        return arch, view