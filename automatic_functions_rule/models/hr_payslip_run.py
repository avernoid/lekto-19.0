from odoo import models


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    def generate_payslips(self, version_ids=None, employee_ids=None):
        res = super().generate_payslips(version_ids=version_ids, employee_ids=employee_ids)
        for payslip in self.slip_ids:
            payslip._onchange_employee()
        return res
