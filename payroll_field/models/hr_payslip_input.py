from dateutil.relativedelta import relativedelta
from lxml import etree
from odoo import models, fields, api


class HrPayslipInput(models.Model):
    _inherit = 'hr.payslip.input'

    date_from = fields.Date(
        string='Date From',
        help='Start date of the payslip period this input belongs to.',
        related='payslip_id.date_from'
    )
    date_to = fields.Date(
        string='Date To',
        help='End date of the payslip period this input belongs to.',
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
        help='Employee associated with this payslip input.',
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
        help='Batch or Pay Run to which this input belongs.',
        related='payslip_id.payslip_run_id',
        store=True,
    )

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super(HrPayslipInput, self)._get_view(view_id, view_type, **options)
        hr_payslip = self.env['hr.payslip.line']
        if view_type in ('search'):
            arch = hr_payslip.set_filter_six_month_before(arch)
        return arch, view
