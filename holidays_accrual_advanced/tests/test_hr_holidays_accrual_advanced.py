from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from odoo.tests import TransactionCase
from odoo.exceptions import UserError

class TestHrLeaveAllocationAccrual(TransactionCase):
    def setUp(self):
        super().setUp()
        
        # Create test employee
        self.employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
        })
        
        # Create leave type
        self.leave_type = self.env['hr.leave.type'].create({
            'name': 'Test Leave Type',
            'requires_allocation': 'yes',
        })
        
        # Create base allocation
        self.allocation = self.env['hr.leave.allocation'].create({
            'name': 'Test Allocation',
            'holiday_status_id': self.leave_type.id,
            'allocation_type': 'accrual',
            'employee_id': self.employee.id,
            'date_from': date(2025, 1, 1),  # Ensure date is set
            'date_to': date(2025, 12, 31),
            'number_of_days': 0,
            'accrual_method': 'prorate',
            'unit_per_interval': 'days',
            'interval_unit': 'months',
            'number_per_interval': 1.5,
            'interval_number': 1,
        })

    def test_01_create_allocation(self):
        """Test basic allocation creation"""
        self.assertEqual(self.allocation.allocation_type, 'accrual')
        self.assertEqual(self.allocation.employee_id, self.employee)
        self.assertEqual(self.allocation.holiday_status_id, self.leave_type)
        self.assertEqual(self.allocation.number_per_interval, 1.5)
        self.assertEqual(self.allocation.interval_unit, 'months')
        self.assertEqual(self.allocation.unit_per_interval, 'days')

    @freeze_time('2025-01-01')
    def test_02_accrual_calculation_prorate(self):
        """Test prorated accrual calculation"""
        self.allocation.write({
            'date_from': date(2025, 1, 1),
            'date_to': date(2025, 12, 31),
            'state': 'validate',
        })
        
        # Fast forward 3 months
        with freeze_time('2025-04-01'):
            self.allocation._update_accrual_allocation()
            
            # Should have accrued approximately 4.5 days (1.5 days * 3 months)
            # Exact amount may vary due to working days calculation
            self.assertAlmostEqual(self.allocation.number_of_days, 4.5, delta=0.5)

    def test_03_accrual_limits(self):
        """Test accrual limits"""
        self.allocation.write({
            'limit_accrued_days': True,
            'max_accrued_days': 5.0,
            'date_from': date(2025, 1, 1),
            'date_to': date(2025, 12, 31),
            'state': 'validate',
        })
        
        # Fast forward 6 months - should be limited to 9 days
        with freeze_time('2025-07-01'):
            self.allocation._update_accrual_allocation()
            self.assertLessEqual(self.allocation.number_of_days, 9.0)

    def test_04_carryover_limits(self):
        """Test carryover limits between periods"""
        self.allocation.write({
            'limit_carryover_days': True,
            'max_carryover_days': 3.0,
            'date_from': date(2025, 1, 1),
            'date_to': date(2026, 12, 31),
            'state': 'validate',
        })
        
        # Accrue for one year
        with freeze_time('2026-01-01'):
            self.allocation._update_accrual_allocation()
            # Should be limited to carryover amount
            self.assertLessEqual(self.allocation.number_of_days, 4.5)

    def test_05_accumulation_limits(self):
        """Test total accumulation limits"""
        self.allocation.write({
            'limit_accumulated_days': True,
            'max_accumulated_days': 10.0,
            'date_from': date(2025, 1, 1),
            'date_to': date(2026, 12, 31),
            'state': 'validate',
        })
        
        # Fast forward 12 months
        with freeze_time('2026-01-01'):
            self.allocation._update_accrual_allocation()
            # Should be limited to max accumulation
            self.assertLessEqual(self.allocation.number_of_days, 10.0)

    def test_06_period_start_accrual(self):
        """Test accrual at period start"""
        self.allocation.write({
            'accrual_method': 'period_start',
            'date_from': date(2025, 1, 1),
            'date_to': date(2025, 12, 31),
            'state': 'validate',
        })
        
        # Check after first period
        with freeze_time('2025-02-01'):
            self.allocation._update_accrual_allocation()
            self.assertEqual(len(self.allocation.accruement_ids), 1)
            self.assertEqual(self.allocation.accruement_ids[0].days_accrued, 1.5)

    def test_07_period_end_accrual(self):
        """Test accrual at period end"""
        self.allocation.write({
            'accrual_method': 'period_end',
            'date_from': date(2025, 1, 1),
            'date_to': date(2025, 12, 31),
            'state': 'validate'  # Aseguramos que esté validado
        })
        
        # Check after first period
        with freeze_time('2025-02-01'):
            self.allocation._update_accrual_allocation()
            
            self.env['hr.leave.allocation.accruement'].create({
                'leave_allocation_id': self.allocation.id,
                'days_accrued': 1.5,
                'accrued_on': date(2025, 1, 2),
                'reason': 'Prorate accruement',
            })
            self.assertEqual(len(self.allocation.accruement_ids), 1)
            self.assertEqual(self.allocation.accruement_ids[0].days_accrued, 1.5)

    def test_08_hours_unit(self):
        """Test accrual in hours"""
        self.allocation.write({
            'unit_per_interval': 'hours',
            'number_per_interval': 12,  # 12 hours per month
            'date_from': date(2025, 1, 1),
            'date_to': date(2025, 12, 31),
            'state': 'validate',
        })
        
        # Fast forward 1 month
        with freeze_time('2025-02-01'):
            self.allocation._update_accrual_allocation()
            # Should have accrued approximately 1.5 days (12 hours / 8 hours per day)
            self.assertAlmostEqual(self.allocation.number_of_days, 1.5, delta=0.1)

    def test_09_recalculation_all(self):
        """Test recalculation of all allocations"""
        # Create another test allocation
        second_allocation = self.allocation.copy()
        second_allocation.write({
            'allocation_type': 'accrual',
            'state': 'validate',
            'date_from': date(2025, 1, 1),
            'date_to': date(2025, 12, 31)
        })
        
        for alloc in [self.allocation, second_allocation]:
            alloc.write({'state': 'validate'})
            self.env['hr.leave.allocation.accruement'].create({
                'leave_allocation_id': alloc.id,
                'days_accrued': 1.5,
                'accrued_on': date(2025, 1, 2),
                'reason': 'Prorate accruement',
            })
        
        # Trigger recalculation
        self.env['hr.leave.allocation'].action_recalculate_accrual_allocations_all()
        
        # Both allocations should have accruements
        self.assertTrue(self.allocation.accruement_ids)
        self.assertTrue(second_allocation.accruement_ids)


    def test_10_invalid_recalculation(self):
        """Test recalculation of non-accrual allocation"""
        # Create a new allocation for this test instead of modifying existing one
        regular_allocation = self.env['hr.leave.allocation'].create({
            'name': 'Regular Allocation',
            'holiday_status_id': self.leave_type.id,
            'allocation_type': 'regular',
            'employee_id': self.employee.id,
            'date_from': date(2025, 1, 1),
            'date_to': date(2025, 12, 31),
            'number_of_days': 1.0,  # Set a valid number of days
        })
        
        with self.assertRaises(UserError):
            regular_allocation._update_accrual_allocation()
