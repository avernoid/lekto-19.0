from odoo import fields
from odoo.tests import common

from dateutil.relativedelta import relativedelta
from datetime import date

@common.tagged('post_install', '-at_install')
class TestHrEmployeeService(common.TransactionCase):

    def setUp(self):
        super().setUp()

        self.today = fields.Date.today()
        self.Employee = self.env['hr.employee']
        self.SudoEmployee = self.Employee.sudo()

    def create_employee_with_version(self, name, start_date, active=True):
        """Helper to create employee with a version (contract)"""
        # Create employee (automatically creates a delegate version with date=Today)
        employee = self.SudoEmployee.create({'name': name})
        
        # Update the automatically created delegate version
        # to match our test requirements (avoiding unique constraint collision on 'Today')
        # We explicitly set date_version and contract_date_start
        employee.version_id.write({
            'date_version': start_date,
            'contract_date_start': start_date,
            'active': active,
        })
        return employee

    def test_service_duration_calculation(self):
        """Test calculation of service duration years, months, days"""
        hire_date = self.today - relativedelta(years=2)
        # Sets up employee with version @ hire_date
        employee = self.create_employee_with_version('Employee Duration Test', hire_date)
        
        # Set start date matching hire date
        employee.service_start_date = hire_date
        employee.contract_date_end = False

        self.assertEqual(employee.service_hire_date, hire_date, "Hire date should be computed from version")
        self.assertEqual(employee.service_duration_years, 2)
        self.assertEqual(employee.service_duration_months, 0)
        self.assertEqual(employee.service_duration_days, 0)

    def test_service_duration_with_termination(self):
        """Test calculation with a termination date"""
        hire_date = self.today - relativedelta(years=3)
        termination_date = self.today - relativedelta(years=1)
        
        employee = self.create_employee_with_version('Employee Terminated', hire_date)
        employee.service_start_date = hire_date
        employee.contract_date_end = termination_date

        self.assertEqual(employee.service_duration_years, 2)

    def test_service_hire_date_computation(self):
        """Test that service_hire_date is correctly computed from the oldest active version"""
        date_old = self.today - relativedelta(years=5)
        # Ensure the old contract ends before the new one starts to avoid "overlapping period" error
        date_old_end = self.today - relativedelta(years=3) 
        date_new = self.today - relativedelta(years=2)

        # 1. Create Employee (Creates Delegate Version @ Today)
        employee = self.SudoEmployee.create({'name': 'Employee Versions'})
        
        # 2. Update Delegate Version to be the "New" version
        employee.version_id.write({
            'date_version': date_new,
            'contract_date_start': date_new,
            'active': True
        })

        # 3. Create "Old" Version explicitly
        self.env['hr.version'].sudo().create({
            'employee_id': employee.id,
            'date_version': date_old,
            'contract_date_start': date_old,
            'contract_date_end': date_old_end, # Must end before the next one starts
            'active': True
        })
        
        # Should pick the oldest one (date_old)
        self.assertEqual(employee.service_hire_date, date_old)

    def test_ignore_archived_versions(self):
        """Test that archived versions are ignored"""
        date_active = self.today - relativedelta(years=1)
        date_archived = self.today - relativedelta(years=10)

        # 1. Create Employee (Creates Delegate Version @ Today)
        employee = self.SudoEmployee.create({'name': 'Employee Archived Version'})
        
        # 2. Update Delegate Version to be the "Active" one
        employee.version_id.write({
            'date_version': date_active,
            'contract_date_start': date_active,
            'active': True
        })

        # 3. Create "Archived" Version
        self.env['hr.version'].sudo().create({
            'employee_id': employee.id,
            'date_version': date_archived,
            'contract_date_start': date_archived,
            'active': False
        })

        # Start date should be date_active (ignoring the older archived one)
        self.assertEqual(employee.service_hire_date, date_active)

    def test_onchange_behavior_simulation(self):
        """
        Test the _onchange_service_hire_date method logic explicitly.
        """
        hire_date = self.today - relativedelta(months=6)
        employee = self.create_employee_with_version('Employee Onchange', hire_date)
        
        self.assertFalse(employee.service_start_date)
        self.assertEqual(employee.service_hire_date, hire_date)

        employee._onchange_service_hire_date()
        
        self.assertEqual(employee.service_start_date, hire_date, "Onchange should copy hire date to start date if empty")
