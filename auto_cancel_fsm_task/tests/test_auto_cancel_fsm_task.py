from datetime import datetime, timedelta
from odoo.tests.common import TransactionCase
from odoo import fields

class TestAutoCancelFsmTask(TransactionCase):

    def setUp(self):
        super(TestAutoCancelFsmTask, self).setUp()
        self.Project = self.env['project.project']
        self.Task = self.env['project.task']

        # Create a test project
        self.project_test = self.Project.create({
            'name': 'Test Project Auto Cancel',
            'antiquity_in_hours': 24, # 24 hours
        })

        # Create a test task, expired (deadline < limit_date)
        # Limit date = Now - 24h
        # Deadline = Now - 26h (so it expired 2h ago relative to the limit)
        self.task_expired = self.Task.create({
            'name': 'Task Expired',
            'project_id': self.project_test.id,
            'date_deadline': fields.Date.today() - timedelta(days=2),
        })

        # Create a test task, NOT expired
        # Deadline = Tomorrow
        self.task_active = self.Task.create({
            'name': 'Task Active',
            'project_id': self.project_test.id,
            'date_deadline': fields.Date.today() + timedelta(days=1),
        })

    def test_cron_auto_cancel(self):
        """ Test that the cron correctly cancels expired tasks """
        # Run the cron logic manually
        # Ideally we'd mock the time, but for logic check relative times are OK.
        # However, our logic relies on fields.Datetime.now()
        
        # Override antiquity to be very small to force expiration relative to now for the 'expired' task
        # Current logic: limit_date = now - antiquity
        # task.deadline < limit_date
        # self.task_expired.deadline is 2 days ago.
        # limit_date = now - 24h = 1 day ago.
        # 2 days ago < 1 day ago. Should cancel.
        
        self.Task._cron_auto_cancel_tasks(project_id=self.project_test.id)

        # Refresh tasks
        self.task_expired.invalidate_recordset()
        self.task_active.invalidate_recordset()

        # Check Task Expired
        self.assertTrue(self.task_expired.not_executed, "Expired task should be marked as not_executed")
        self.assertEqual(self.task_expired.state, '1_done', "Expired task should be in '1_done' state")

        # Check Task Active
        self.assertFalse(self.task_active.not_executed, "Active task should NOT be marked as not_executed")
        self.assertNotEqual(self.task_active.state, '1_done', "Active task should NOT be '1_done' yet")
