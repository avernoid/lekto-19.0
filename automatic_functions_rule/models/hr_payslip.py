from odoo import models, fields, api, _
from odoo.tools import float_round, date_utils
from odoo.tools.misc import format_date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from collections import defaultdict
from datetime import datetime

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _remove_zero_salary_lines(self):
        for rec in self:
            rec.line_ids.filtered(lambda l: l.total == 0).unlink()

    def _remove_zero_worked_days(self):
        for rec in self:
            rec.worked_days_line_ids.filtered(
                lambda l: l.number_of_days == 0
            ).unlink()

    def _remove_zero_inputs(self):
        for rec in self:
            rec.input_line_ids.filtered(
                lambda l: l.amount == 0
            ).unlink()

    def action_remove_zeros(self):
        self._remove_zero_salary_lines()
        self._remove_zero_worked_days()
        self._remove_zero_inputs()

    def action_payslip_done(self):
        super(HrPayslip, self).action_payslip_done()
        for rec in self:
            days_lines = rec.worked_days_line_ids.filtered(lambda x: x.number_of_days == 0)
            days_lines.unlink()
            input_lines = rec.input_line_ids.filtered(lambda x: x.amount == 0)
            input_lines.unlink()

    @api.onchange('employee_id', 'struct_id','version_id', 'date_from', 'date_to')
    def _onchange_employee(self):
        self._compute_worked_days_line_ids()
        self._compute_name()
        self.get_inputs()

    def get_inputs_data(self):
        input_values = []
        input_ids = self.struct_id.input_line_type_ids

        utilities_model = self.env['ir.model'].sudo().search([
            ('model', '=', 'data.utilities')
        ])

        utilities = self.env['data.utilities'].search(
            [('is_active', '=', True)],
            limit=1
        ) if utilities_model else False

        for input_line in input_ids:
            if utilities:
                if input_line.code == 'UTL_003':
                    amount = utilities.factor_days
                elif input_line.code == 'UTL_004':
                    amount = utilities.factor_amount
                else:
                    amount = 0
            else:
                amount = 0

            input_values.append({
                'input_type_id': input_line.id,
                'code': input_line.code,
                'name': input_line.name,
                'amount': amount,
            })

        return input_values

    def get_inputs(self):
        self.ensure_one()
        input_values = self.get_inputs_data()
        input_lines = self.input_line_ids.browse([])
        for values in input_values:
            input_lines |= input_lines.new(values)
        self.input_line_ids = input_lines

    def compute_sheet(self):
        res = super().compute_sheet()
        self._remove_zero_salary_lines()
        return res
