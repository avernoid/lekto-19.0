from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError

class TestFsmSaleLostReason(TransactionCase):

    def setUp(self):
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info("Setting up TestFsmSaleLostReason")
        super(TestFsmSaleLostReason, self).setUp()
        self.Project = self.env['project.project']
        self.Task = self.env['project.task']
        self.LostReason = self.env['sale.lost.reason']
        self.Wizard = self.env['project.task.lost.reason.wizard']

        # Create a lost reason
        self.lost_reason = self.LostReason.create({'name': 'Too Expensive'})

        # Create a project with use_lost_reason enabled
        # Create or find a project with use_lost_reason enabled
        self.fsm_project = self.env['project.project'].search([('is_fsm', '=', True), ('company_id', '=', self.env.ref('base.main_company').id)], limit=1)
        if not self.fsm_project:
            _logger.info("Creating new FSM Project")
            self.fsm_project = self.Project.create({
                'name': 'FSM Project',
                'is_fsm': True,
                'company_id': self.env.ref('base.main_company').id,
            })
        self.fsm_project.write({'use_lost_reason': True})

        # Create a task
        self.task = self.Task.create({
            'name': 'Test Task',
            'project_id': self.fsm_project.id,
        })
        _logger.info("Setup complete")

    def test_lost_reason_required(self):
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info("Running test_lost_reason_required")
        """ Test that lost reason is required when marking as done without SO """
        # Try to mark as done (simulate action_fsm_validate)
        # We use skip_fsm_super to avoid standard FSM errors, but here we expect the wizard BEFORE super is called.
        action = self.task.with_context(skip_fsm_super=True).action_fsm_validate()

        # Should return a wizard action
        self.assertIsInstance(action, dict)
        self.assertEqual(action.get('res_model'), 'project.task.lost.reason.wizard')

        # Create wizard and confirm
        # Pass skip_fsm_super so that when wizard calls validate again, it succeeds (returns True)
        wizard = self.Wizard.with_context(active_id=self.task.id, skip_fsm_super=True).create({
            'task_id': self.task.id,
            'lost_reason_id': self.lost_reason.id,
        })
        res = wizard.action_confirm()

        # Task should have lost reason set
        self.assertEqual(self.task.lost_reason_id, self.lost_reason)
        # Result should be True (from our skip logic)
        self.assertTrue(res)
        _logger.info("test_lost_reason_required passed")

    def test_lost_reason_not_required_if_so_confirmed(self):
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info("Running test_lost_reason_not_required_if_so_confirmed")
        """ Test that lost reason is NOT required if SO is confirmed """
        # Create a SO linked to the task (mocking the link)
        partner = self.env['res.partner'].create({'name': 'Test Partner'})
        sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
            'task_id': self.task.id,
            'state': 'sale', # Confirmed
        })
        self.task.sale_order_id = sale_order

        # Try to mark as done
        # Should NOT return a wizard action. Should return True (because of skip_fsm_super).
        res = self.task.with_context(skip_fsm_super=True).action_fsm_validate()
        
        if isinstance(res, dict):
             self.assertNotEqual(res.get('res_model'), 'project.task.lost.reason.wizard')
        else:
             self.assertTrue(res)
        _logger.info("test_lost_reason_not_required_if_so_confirmed passed")

    def test_lost_reason_not_required_if_project_disabled(self):
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info("Running test_lost_reason_not_required_if_project_disabled")
        """ Test that lost reason is NOT required if project setting is disabled """
        self.fsm_project.use_lost_reason = False
        
        res = self.task.with_context(skip_fsm_super=True).action_fsm_validate()
        if isinstance(res, dict):
             self.assertNotEqual(res.get('res_model'), 'project.task.lost.reason.wizard')
        else:
             self.assertTrue(res)
        _logger.info("test_lost_reason_not_required_if_project_disabled passed")
