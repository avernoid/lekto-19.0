from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError
from odoo import SUPERUSER_ID

class TestPortalCompletion(TransactionCase):
    
    def setUp(self):
        super().setUp()
        # 1. Create Portal User with Robust Group Setup (See portal_patterns.md)
        self.portal_user = self.env['res.users'].create({
            'name': 'Portal Tester',
            'login': 'portal_tester_complete',
            'email': 'portal_complete@test.com',
        })
        # Important: Remove 'Internal User' before adding 'Portal'
        self.env.ref('base.group_user').write({'user_ids': [(3, self.portal_user.id)]})
        self.env.ref('base.group_portal').write({'user_ids': [(4, self.portal_user.id)]})
        
        # 2. Create Project & Task (Sudo to avoid permission issues during setup)
        self.project = self.env['project.project'].sudo().create({
            'name': 'Test Project',
            'evidence_final_state': '1_done',
            'force_min_photos': False 
        })
        
        self.task = self.env['project.task'].sudo().create({
            'name': 'Test Task',
            'project_id': self.project.id,
            'user_ids': [(4, self.portal_user.id)],
            'state': '01_in_progress'
        })

    def test_portal_can_complete_task(self):
        """ Test that a portal user can mark a task as done (which triggers a write on state) """
        
        # Scenario: 
        # Portal User clicks a button that hits a Controller.
        # The controller does: task.sudo().write(...)
        
        # We simulate the environment of the Portal User
        task_as_portal = self.task.with_user(self.portal_user)
        
        # PROVE FAIL: Direct write should fail
        # with self.assertRaises(AccessError):
        #     task_as_portal.write({'state': '1_done'})
            
        # PROVE SUCCESS: Controller Logic (Sudo write)
        # This mirrors the controller code: 'task = request.env[...].sudo().browse(...)'
        
        # CRITICAL: Even with sudo(), 'env.user' remains the Portal User in the context
        # unless with_user(SUPERUSER_ID) is used.
        # If any automation checks env.user.groups_id, it will crash.
        
        task_sudo_context_portal = task_as_portal.sudo()
        
        # This is the exact line executed by the controller
        task_sudo_context_portal.write({'state': '1_done'})
        
        # Verify
        self.assertEqual(self.task.state, '1_done', "Task should be in Done state")

    def test_portal_validation_missing_evidence(self):
        """ Test that the validation logic correctly identifies missing photos for a portal user """
        
        # 1. Setup Evidence Requirement on a Product
        # The fields are on product.product (inherited from product.template)
        evidence_product = self.env['product.product'].create({
            'name': 'Required Photo Item',
            'type': 'service',
            'evidence_required': True,
            'evidence_min_qty': 1
        })
        
        # Enable enforcement on project
        self.project.write({
            'force_min_photos': True,
        })
        
        # Link product to task (Where the field actually exists)
        self.task.write({
            'evidence_product_ids': [(4, evidence_product.id)]
        })
        
        # 2. Simulate Portal User Context
        task_as_portal = self.task.with_user(self.portal_user)
        
        # 3. Call validation method (This previously crashed if user couldn't read logic)
        missing = task_as_portal._get_missing_evidence_requirements()
        
        # 4. Assertions
        self.assertTrue(missing, "Should report missing evidence")
        self.assertEqual(missing[0]['product_name'], 'Required Photo Item', "Should identify correct product")
        self.assertEqual(missing[0]['required'], 1, "Should show correct required qty")
        self.assertEqual(missing[0]['current'], 0, "Should show correct current qty")
