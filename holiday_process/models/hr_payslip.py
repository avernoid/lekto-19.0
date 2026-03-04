from odoo import models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _get_worked_day_lines(self, domain=None, check_out_of_contract=True):
        res = super(HrPayslip, self)._get_worked_day_lines(domain,check_out_of_contract)
        employee_id = self.version_id.employee_id

        if self.version_id.resource_calendar_id and employee_id.service_termination_date:
            leave_23 = self.env.ref('holiday_process.hr_leave_type_23')
            leaves = self.env['hr.leave'].search([
                ('holiday_status_id.id', '=', leave_23.id),
                ('employee_id', '=', employee_id.id),
                ('name', '=like', 'Esta ausencia no ha sido gozada%'),
                ('state', 'in', ['validate1', 'validate']),
            ])

            # VAC_LBS
            vac_lbs_days = sum(leaves.mapped('number_of_days'))
            hours_per_day = self.version_id.resource_calendar_id.hours_per_day or 0.0
            vac_lbs_hours = vac_lbs_days * hours_per_day
            vac_lbs_entry_type_id = self.env.ref('holiday_process.hr_work_entry_type_vac_lbs')

            values = [{
                'sequence': vac_lbs_entry_type_id.sequence, 'work_entry_type_id': vac_lbs_entry_type_id.id, 'number_of_days': vac_lbs_days,
                'number_of_hours': vac_lbs_hours
            }]
            res += values
        return res
