from datetime import datetime
from odoo.addons.hr_payroll.tests.common import TestPayslipBase


class TestPayslipFlow(TestPayslipBase):

    def test_00_payslip_flow(self):
        """ Testing payslip flow """

        self.richard_emp.version_ids[0].contract_date_start = datetime(2025, 1, 1).date()
        self.richard_emp.version_ids[0].contract_date_end = datetime(2025, 12, 31).date()

        richard_payslip = self.env['hr.payslip'].create({
            'name': 'Payslip of Richard',
            'employee_id': self.richard_emp.id,
        })
        self.assertEqual(richard_payslip.name, 'Payslip of Richard')

    def test_01_payslip_flow(self):
        """ Create a payslip with expired contract """

        self.richard_emp.version_ids[0].contract_date_end = datetime(2022, 1, 1).date()

        richard_payslip = self.env['hr.payslip'].create({
            'name': 'Payslip of Richard',
            'employee_id': self.richard_emp.id,
        })

        self.assertEqual(richard_payslip.name, 'Payslip of Richard')
