import logging

from datetime import date

from odoo.tests import common

_logger = logging.getLogger(__name__)


class TestHrLeaveAllocation(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.Employee = self.env['hr.employee']
        self.SudoEmployee = self.Employee.sudo()

        self.dep_rd = self.env['hr.department'].create({
            'name': 'Research & Development - Test',
        })

        self.hr_leave_allocation_model = self.env['hr.leave.allocation']
        self.hr_leave_model = self.env['hr.leave']
        _logger.info("------SETUP START---- COMPLETE------")

    def test_leave_allocation_fields(self):

        self.employee = self.SudoEmployee.create({
            'name': 'Richard',
            'sex': 'male',
            'birthday': '1984-05-01',
            'country_id': self.env.ref('base.be').id,
            'department_id': self.dep_rd.id,
        })
        _logger.info("------EMPLOYEE CREATED SUCCESSFULLY---- COMPLETE------")

        self.leave_type = self.env['hr.leave.type'].create({
            'name': 'Unlimited',
            'leave_validation_type': 'hr',
            'requires_allocation': 'no',
        })
        _logger.info("------LEAVE TYPE CREATED SUCCESSFULLY---- COMPLETE------")

        leave_allocation = self.hr_leave_allocation_model.sudo().create({
            'name': 'Test Leave Allocation',
            'employee_id': self.employee.id,
            'holiday_status_id': self.leave_type.id,
            'number_of_days': 5,
        })
        leave_allocation.sudo()._action_validate()
        _logger.info("--------LEAVE ALLOCATION CREATED AND VALIDATED SUCCESSFULLY---------")

        leave = self.hr_leave_model.sudo().create({
            'name': 'Test Leave',
            'employee_id': self.employee.id,
            'holiday_status_id': leave_allocation.holiday_status_id.id,
            'date_from': date(2023, 4, 5),
            'date_to': date(2023, 4, 7),
        })
        _logger.info("--------LEAVE CREATED SUCCESSFULLY---------")

        self.assertEqual(leave.employee_id, self.employee)
        self.assertEqual(leave.holiday_status_id, self.leave_type)
        self.assertIn(leave_allocation.name, 'Test Leave Allocation')
        _logger.info("--------ASSERTIONS COMPLETED---------")
