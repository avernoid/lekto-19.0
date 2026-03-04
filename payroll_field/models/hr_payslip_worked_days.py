from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from datetime import datetime
from lxml import etree

class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    date_from = fields.Date(
        string='Date From',
        help='Start date of the payslip period this worked days record belongs to.',
        related='payslip_id.date_from'
    )
    date_to = fields.Date(
        string='Date To',
        help='End date of the payslip period this worked days record belongs to.',
        related='payslip_id.date_to'
    )
    date_start = fields.Char(
        string='Month/Year',
        help='Text representation (MM/YYYY) of the payroll month.',
        related='payslip_id.date_start'
    )
    date_start_dt = fields.Date(
        string='Payroll Month',
        help='Computed payroll month date. Used for analysis grouping by period.',
        related='payslip_id.date_start_dt',
        store=True
    )
    employee_id = fields.Many2one(
        string='Employee',
        help='Employee associated with this worked days record.',
        related='payslip_id.employee_id'
    )
    state = fields.Selection(
        string='Status',
        help='Current status of the payslip (Draft, Waiting, Done, etc.).',
        related='payslip_id.state'
    )
    department_id = fields.Many2one(
        comodel_name='hr.department',
        string='Department',
        help='Department of the employee, used for filtering and grouping.',
        related='employee_id.department_id'
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        help='Company of the payslip.',
        related='payslip_id.company_id',
    )
    disability = fields.Boolean(
        string='Disability',
        help='Whether the employee has a registered disability.',
        related='employee_id.disability'
    )
    struct_id = fields.Many2one(
        comodel_name='hr.payroll.structure',
        string='Structure',
        help='Payroll structure used for this payslip.',
        related='payslip_id.struct_id'
    )
    payslip_run_id = fields.Many2one(
        comodel_name='hr.payslip.run',
        string='Pay Run / Lote',
        help='Batch or Pay Run to which this worked day record belongs.',
        related='payslip_id.payslip_run_id',
        store=True,
    )
  
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super(HrPayslipWorkedDays, self)._get_view(view_id, view_type, **options)
        hr_payslip = self.env['hr.payslip.line']
        if view_type in ('search'):
            arch = hr_payslip.set_filter_six_month_before(arch)
        return arch, view
    
    @api.depends('work_entry_type_id', 'number_of_days', 'number_of_hours', 'payslip_id.date_from', 'payslip_id.date_to')
    def _compute_name(self):
        if not self.payslip_id.ids:
            day_to_payslips = datetime.now().strftime('%Y-%m-%d')
            day_from_payslips = datetime.now().strftime('%Y-%m-%d')
        else:
            day_to_payslips = max(self.payslip_id.mapped('date_to'))
            day_from_payslips=min(self.payslip_id.mapped('date_from'))
        to_check_public_holiday = {
            res[0]: res[1]
            for res in self.env['resource.calendar.leaves']._read_group(
                [
                    ('resource_id', '=', False),
                    ('work_entry_type_id', 'in', self.mapped('work_entry_type_id').ids),
                    ('date_from', '<=', day_to_payslips),
                    ('date_to', '>=', day_from_payslips),
                ],
                ['work_entry_type_id'],
                ['id:recordset']
            )
        }
        for worked_days in self:
            public_holidays = to_check_public_holiday.get(worked_days.work_entry_type_id, '')
            holidays = public_holidays and public_holidays.filtered(lambda p:
               (p.calendar_id.id == worked_days.employee_id.resource_calendar_id.id or not p.calendar_id.id)
                and p.date_from.date() <= worked_days.payslip_id.date_to
                and p.date_to.date() >= worked_days.payslip_id.date_from
                and p.company_id == worked_days.payslip_id.company_id)
            half_day = worked_days._is_half_day()
            if holidays:
                name = (', '.join(holidays.mapped('name')))
            else:
                name = worked_days.work_entry_type_id.name
            worked_days.name = name
