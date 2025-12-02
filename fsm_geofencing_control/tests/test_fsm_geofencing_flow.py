from odoo.tests import TransactionCase
from odoo.exceptions import UserError, ValidationError
from unittest.mock import patch


class TestFSMGeofencingFlow(TransactionCase):
    """Test complete FSM geofencing flow."""

    def setUp(self):
        super().setUp()
        
        # Mock _get_localisation to avoid request object error in tests
        self.patcher = patch('odoo.addons.base_geolocalize.models.base_geocoder.BaseGeocoder._get_localisation')
        self.mock_get_localisation = self.patcher.start()
        self.mock_get_localisation.return_value = 'Test Location'
        
        # Create a customer with geolocation (New York coordinates)
        self.customer = self.env['res.partner'].create({
            'name': 'Test Customer',
            'partner_latitude': 40.7128,
            'partner_longitude': -74.0060,
        })
        
        # Create a customer without geolocation
        self.customer_no_geo = self.env['res.partner'].create({
            'name': 'Customer Without Geo',
            'partner_latitude': 0.0,
            'partner_longitude': 0.0,
        })
        
        # Create FSM project with geolocation enabled
        # Use existing FSM project from industry_fsm demo data
        self.project = self.env.ref('industry_fsm.fsm_project')
        self.project.write({
            'allow_timesheets': True,
            'allow_geolocation': True,
            'control_distance_on_start': True,
            'control_distance_on_stop': True,
            'allowed_distance': 1000.0,  # 1000 m
        })
        
        
        # Create an employee for the current user
        self.employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
            'user_id': self.env.uid,
            'company_id': self.env.company.id,
        })
        
        # Create a lost reason
        self.lost_reason = self.env['sale.lost.reason'].create({
            'name': 'Customer not interested',
        })

    def tearDown(self):
        """Stop the patcher after each test."""
        self.patcher.stop()
        super().tearDown()

    def test_start_timer_within_distance(self):
        """Test starting timer when within allowed distance."""
        task = self.env['project.task'].create({
            'name': 'Test Task',
            'project_id': self.project.id,
            'partner_id': self.customer.id,
        })
        
        # Simulate geolocation very close to customer (0.5 km away)
        geolocation = {
            'success': True,
            'latitude': 40.7173,  # ~0.5 km north
            'longitude': -74.0060,
        }
        
        # Should not raise error
        task.with_context(geolocation=geolocation).action_timer_start()
        
        # Check that location was stored
        self.assertAlmostEqual(task.last_latitude, 40.7173, places=4)
        self.assertAlmostEqual(task.last_longitude, -74.0060, places=4)

    def test_start_timer_outside_distance(self):
        """Test starting timer when outside allowed distance."""
        task = self.env['project.task'].create({
            'name': 'Test Task',
            'project_id': self.project.id,
            'partner_id': self.customer.id,
        })
        
        # Simulate geolocation far from customer (Los Angeles, ~3935 km away)
        geolocation = {
            'success': True,
            'latitude': 34.0522,
            'longitude': -118.2437,
        }
        
        # Should raise UserError
        with self.assertRaises(UserError) as cm:
            task.with_context(geolocation=geolocation).action_timer_start()
        
        self.assertIn('too far', str(cm.exception))

    def test_start_timer_no_customer_geolocation(self):
        """Test starting timer when customer has no geolocation."""
        task = self.env['project.task'].create({
            'name': 'Test Task',
            'project_id': self.project.id,
            'partner_id': self.customer_no_geo.id,
        })
        
        geolocation = {
            'success': True,
            'latitude': 40.7128,
            'longitude': -74.0060,
        }
        
        # Should raise UserError
        with self.assertRaises(UserError) as cm:
            task.with_context(geolocation=geolocation).action_timer_start()
        
        self.assertIn('does not have a valid geolocation', str(cm.exception))

    def test_start_timer_control_disabled(self):
        """Test starting timer when distance control is disabled."""
        self.project.write({
            'control_distance_on_start': False,
        })
        
        task = self.env['project.task'].create({
            'name': 'Test Task',
            'project_id': self.project.id,
            'partner_id': self.customer.id,
        })
        
        # Simulate geolocation far from customer
        geolocation = {
            'success': True,
            'latitude': 34.0522,
            'longitude': -118.2437,
        }
        
        # Should not raise error because control is disabled
        task.with_context(geolocation=geolocation).action_timer_start()

    def test_stop_timer_with_lost_reason(self):
        """Test stopping timer with lost reason when no sale order."""
        # Enable lost reason requirement
        self.project.write({'use_lost_reason': True})
        
        task = self.env['project.task'].create({
            'name': 'Test Task',
            'project_id': self.project.id,
            'partner_id': self.customer.id,
        })
        
        # Start timer
        geolocation_start = {
            'success': True,
            'latitude': 40.7128,
            'longitude': -74.0060,
        }
        task.with_context(geolocation=geolocation_start).action_timer_start()
        
        # Create timesheet
        timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Timesheet',
            'project_id': self.project.id,
            'task_id': task.id,
            'unit_amount': 1.0,
        })
        
        # Create wizard
        wizard = self.env['hr.timesheet.stop.timer.confirmation.wizard'].create({
            'timesheet_id': timesheet.id,
            'lost_reason_id': self.lost_reason.id,
        })
        
        geolocation_stop = {
            'success': True,
            'latitude': 40.7128,
            'longitude': -74.0060,
        }
        
        # Should not raise error
        wizard.with_context(geolocation=geolocation_stop).action_save_timesheet()
        
        # Check that lost reason was saved
        self.assertEqual(task.lost_reason_id, self.lost_reason)

    def test_stop_timer_without_lost_reason_raises_error(self):
        """Test stopping timer without lost reason raises error."""
        # Enable lost reason requirement
        self.project.write({'use_lost_reason': True})
        
        task = self.env['project.task'].create({
            'name': 'Test Task',
            'project_id': self.project.id,
            'partner_id': self.customer.id,
        })
        
        # Start timer
        geolocation_start = {
            'success': True,
            'latitude': 40.7128,
            'longitude': -74.0060,
        }
        task.with_context(geolocation=geolocation_start).action_timer_start()
        
        # Create timesheet
        timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Timesheet',
            'project_id': self.project.id,
            'task_id': task.id,
            'unit_amount': 1.0,
        })
        
        # Create wizard without lost reason
        wizard = self.env['hr.timesheet.stop.timer.confirmation.wizard'].create({
            'timesheet_id': timesheet.id,
        })
        
        geolocation_stop = {
            'success': True,
            'latitude': 40.7128,
            'longitude': -74.0060,
        }
        
        # Should raise ValidationError
        with self.assertRaises(ValidationError) as cm:
            wizard.with_context(geolocation=geolocation_stop).action_save_timesheet()
        
        self.assertIn('Lost Reason is required', str(cm.exception))

    def test_auto_mark_done(self):
        """Test auto-marking task as done when logging time."""
        self.project.write({'auto_mark_done': True})
        # Invalidate cache to ensure the field value is properly set
        self.project.invalidate_recordset(['auto_mark_done'])
        
        task = self.env['project.task'].create({
            'name': 'Test Task',
            'project_id': self.project.id,
            'partner_id': self.customer.id,
        })
        
        # Start timer
        geolocation_start = {
            'success': True,
            'latitude': 40.7128,
            'longitude': -74.0060,
        }
        task.with_context(geolocation=geolocation_start).action_timer_start()
        
        # Create timesheet
        timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Timesheet',
            'project_id': self.project.id,
            'task_id': task.id,
            'employee_id': self.employee.id,
            'unit_amount': 1.0,
        })
        
        # Create wizard
        wizard = self.env['hr.timesheet.stop.timer.confirmation.wizard'].create({
            'timesheet_id': timesheet.id,
        })
        
        geolocation_stop = {
            'success': True,
            'latitude': 40.7128,
            'longitude': -74.0060,
        }
        
        # Save timesheet
        result = wizard.with_context(geolocation=geolocation_stop).action_save_timesheet()
        
        # Invalidate cache to get updated state
        task.invalidate_recordset()
        
        # Check that task was marked as done
        # Note: We need to check both state and fsm_done
        self.assertTrue(task.fsm_done, "Task should be marked as fsm_done")
        self.assertEqual(task.state, '1_done', f"Task state should be '1_done' but is '{task.state}'")
