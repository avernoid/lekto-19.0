# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError
from odoo import fields

@tagged('post_install', '-at_install', 'attendance_geo')
class TestGeolocationControl(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.address = cls.env['res.partner'].create({
            'name': 'Test Office Address',
        })
        cls.work_location = cls.env['hr.work.location'].create({
            'name': 'Test Office',
            'address_id': cls.address.id,
            'latitude': -12.046374, # Lima center
            'longitude': -77.042793,
        })
        
        cls.job = cls.env['hr.job'].create({
            'name': 'Test Geolocation Job',
            'attendance_geo_enforced': True,
            'attendance_radius_m': 100,
            'out_of_location_policy': 'block',
            'low_accuracy_policy': 'block',
            'accuracy_high_max': 10,
            'accuracy_medium_max': 50,
        })
        
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Geo Employee',
            'job_id': cls.job.id,
            'monday_location_id': cls.work_location.id,
            'tuesday_location_id': cls.work_location.id,
            'wednesday_location_id': cls.work_location.id,
            'thursday_location_id': cls.work_location.id,
            'friday_location_id': cls.work_location.id,
            'saturday_location_id': cls.work_location.id,
            'sunday_location_id': cls.work_location.id,
        })

    def test_01_check_in_inside_radius(self):
        """ Test check-in inside the radius with high accuracy """
        # Lima center point
        vals = {
            'employee_id': self.employee.id,
            'check_in': fields.Datetime.now(),
            'in_latitude': -12.046374,
            'in_longitude': -77.042793,
            'in_accuracy': 5.0,
        }
        attendance = self.env['hr.attendance'].create(vals)
        self.assertEqual(attendance.location_status, 'inside')
        self.assertEqual(attendance.location_reliability, 'high')

    def test_02_check_in_outside_radius_block(self):
        """ Test check-in outside the radius with block policy """
        # Point far away
        vals = {
            'employee_id': self.employee.id,
            'check_in': fields.Datetime.now(),
            'in_latitude': -12.100000,
            'in_longitude': -77.000000,
            'in_accuracy': 5.0,
        }
        with self.assertRaises(ValidationError):
            self.env['hr.attendance'].create(vals)

    def test_03_low_accuracy_block(self):
        """ Test check-in with low accuracy and block policy """
        vals = {
            'employee_id': self.employee.id,
            'check_in': fields.Datetime.now(),
            'in_latitude': -12.046374,
            'in_longitude': -77.042793,
            'in_accuracy': 100.0, # Low accuracy
        }
        with self.assertRaises(ValidationError):
            self.env['hr.attendance'].create(vals)

    def test_04_no_location_policy_block(self):
        """ Test block if no location is assigned for the day """
        # Sunday (usually no location)
        sunday_employee = self.env['hr.employee'].create({'name': 'Sunday Employee'})
        self.company.no_location_policy_default = 'block'
        
        with self.assertRaises(ValidationError):
            self.env['hr.attendance'].create({
                'employee_id': sunday_employee.id,
                'check_in': fields.Datetime.now(),
            })
