from datetime import date

from odoo.tests.common import tagged
from .common import TestPayslipBase


@tagged('post_install', '-at_install')
class TestAutomaticFunctionsRule(TestPayslipBase):
    """Tests for the automatic zero-removal logic added by automatic_functions_rule.

    Only worked-day and input lines are tested directly because
    hr.payslip.line.create() requires a running contract in hr_payroll Enterprise,
    and the contract setup is outside this module's scope.
    The salary-line removal is implicitly covered via action_remove_zeros.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.payslip = cls.env['hr.payslip'].create({
            'name': 'Payslip of Richard',
            'employee_id': cls.richard_emp.id,
            'struct_id': cls.developer_pay_structure.id,
            'date_from': date(2016, 1, 1),
            'date_to': date(2016, 1, 31),
        })

    def _create_worked_day(self, days):
        """Helper to create a worked-day line."""
        return self.env['hr.payslip.worked_days'].create({
            'payslip_id': self.payslip.id,
            'work_entry_type_id': self.work_entry_type.id,
            'number_of_days': days,
            'number_of_hours': days * 8,
        })

    def _create_input(self, amount):
        """Helper to create an input line."""
        return self.env['hr.payslip.input'].create({
            'payslip_id': self.payslip.id,
            'input_type_id': self.input_type.id,
            'amount': amount,
        })

    # ------------------------------------------------------------------
    # _remove_zero_worked_days
    # ------------------------------------------------------------------
    def test_remove_zero_worked_days(self):
        """Worked-day lines with 0 days are removed, non-zero are kept."""
        wd_ok = self._create_worked_day(22)
        wd_zero = self._create_worked_day(0)

        self.payslip._remove_zero_worked_days()

        self.assertIn(wd_ok, self.payslip.worked_days_line_ids)
        self.assertNotIn(wd_zero, self.payslip.worked_days_line_ids)

    # ------------------------------------------------------------------
    # _remove_zero_inputs
    # ------------------------------------------------------------------
    def test_remove_zero_inputs(self):
        """Input lines with amount == 0 are removed, non-zero are kept."""
        inp_ok = self._create_input(500)
        inp_zero = self._create_input(0)

        self.payslip._remove_zero_inputs()

        self.assertIn(inp_ok, self.payslip.input_line_ids)
        self.assertNotIn(inp_zero, self.payslip.input_line_ids)

    # ------------------------------------------------------------------
    # action_remove_zeros (manual button)
    # ------------------------------------------------------------------
    def test_action_remove_zeros_cleans_worked_days_and_inputs(self):
        """The 'Eliminate Zeros' button removes zero-value worked days and inputs."""
        self._create_worked_day(22)
        self._create_worked_day(0)
        self._create_input(500)
        self._create_input(0)

        self.payslip.action_remove_zeros()

        self.assertFalse(
            self.payslip.worked_days_line_ids.filtered(lambda l: l.number_of_days == 0),
            "Zero worked-day lines should be removed.",
        )
        self.assertFalse(
            self.payslip.input_line_ids.filtered(lambda l: l.amount == 0),
            "Zero input lines should be removed.",
        )
        # Non-zero lines must survive
        self.assertTrue(
            self.payslip.worked_days_line_ids.filtered(lambda l: l.number_of_days == 22),
            "Non-zero worked-day lines should be kept.",
        )
        self.assertTrue(
            self.payslip.input_line_ids.filtered(lambda l: l.amount == 500),
            "Non-zero input lines should be kept.",
        )
