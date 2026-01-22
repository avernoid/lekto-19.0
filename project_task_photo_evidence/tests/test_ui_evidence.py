from odoo.tests.common import HttpCase, tagged

@tagged('post_install', '-at_install')
class TestEvidencePortalHttp(HttpCase):
    
    def setUp(self):
        super().setUp()
        # Create a user with portal access
        self.portal_user = self.env['res.users'].create({
            'name': 'Test Portal User',
            'login': 'portal_test',
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])]
        })
        self.portal_user.password = 'portal_test'
        
        # Create a project and task
        self.project = self.env['project.project'].create({'name': 'Test Project'})
        self.task = self.env['project.task'].create({
            'name': 'Test Task',
            'project_id': self.project.id,
            'user_ids': [(6, 0, [self.portal_user.id])],
        })

    def test_evidence_route_crash(self):
        """ Test that the evidence portal route does not crash (500) with various inputs """
        self.authenticate('portal_test', 'portal_test')
        
        # 1. Normal access
        response = self.url_open('/my/evidence/tasks')
        self.assertEqual(response.status_code, 200, "Normal access failed")
        
        # 2. Bad filter_tag (Empty)
        response = self.url_open('/my/evidence/tasks?filter_tag=')
        self.assertEqual(response.status_code, 200, "Empty filter_tag failed")
        
        # 3. Bad filter_tag (String)
        response = self.url_open('/my/evidence/tasks?filter_tag=abc')
        self.assertEqual(response.status_code, 200, "String filter_tag failed")
        
        # 4. Bad filter_product
        response = self.url_open('/my/evidence/tasks?filter_product=xyz')
        self.assertEqual(response.status_code, 200, "String filter_product failed")

        # 5. Bad filter_project
        response = self.url_open('/my/evidence/tasks?filter_project=bad')
        self.assertEqual(response.status_code, 200, "String filter_project failed")
