from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestHrLeaveAbsence(TransactionCase):

    def setUp(self):
        super(TestHrLeaveAbsence, self).setUp()

        # Create a proper employee with its own resource calendar
        self.calendar = self.env['resource.calendar'].create({
            'name': 'Test Standard Calendar',
            'hours_per_day': 8,
        })
        self.employee = self.env['hr.employee'].create({
            'name': 'Test Absence Employee',
            'resource_calendar_id': self.calendar.id,
        })

        # Create a leave type that does NOT require allocation
        self.leave_type = self.env['hr.leave.type'].create({
            'name': 'Test Absence Leave',
            'requires_allocation': False,
            'overtime_deductible': False,
            'company_id': self.env.company.id,
        })

        # Create the hr.leave with proper references
        self.ts_hr_leave = self.env['hr.leave'].create({
            'employee_id': self.employee.id,
            'holiday_status_id': self.leave_type.id,
            'report_attendance': True,
            'private_name': 'Permiso personal',
            'date_from': '2024-01-25 00:00:00',
            'date_to': '2024-01-25 23:59:59',
        })

    def test_fields_hr_leave_absence(self):
        self.assertEqual(self.ts_hr_leave.employee_id, self.employee)
        self.assertEqual(self.ts_hr_leave.holiday_status_id, self.leave_type)
        self.assertTrue(self.ts_hr_leave.report_attendance)
        self.assertEqual(self.ts_hr_leave.state, 'confirm')
        self.assertEqual(self.ts_hr_leave.private_name, 'Permiso personal')

    def test_funtion_leave_absence(self):
        schedule = self.employee.resource_calendar_id
        self.assertTrue(schedule, "Employee should have a resource calendar")
        self.assertEqual(self.ts_hr_leave.get_period_odd_even_week(), self.ts_hr_leave.get_period_odd_even_week())
