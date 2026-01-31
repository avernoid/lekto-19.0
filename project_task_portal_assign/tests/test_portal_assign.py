from odoo.tests.common import TransactionCase, new_test_user

class TestPortalAssign(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_user = new_test_user(cls.env, login='portal_test', groups='base.group_portal')
        # Ensure share is True (it should be by default for portal group, but explicitly check)
        cls.portal_user.partner_id.write({'email': 'portal@test.com'})
        
        cls.internal_user = new_test_user(cls.env, login='internal_test', groups='base.group_user')

        cls.project = cls.env['project.project'].create({
            'name': 'Test Project',
            'allow_portal_user': True,
        })
        
        cls.task = cls.env['project.task'].create({
            'name': 'Test Task',
            'project_id': cls.project.id,
        })

    def test_domain_logic(self):
        """ Test that allow_portal_user affects the computed domain logic (simulation) """
        # Since domain is in XML, we cannot test the UI restriction easily in TransactionCase without HttpCase/Tours.
        # However, we can verify the field values.
        
        self.assertTrue(self.project.allow_portal_user, "Default should be True")
        self.assertTrue(self.task.allow_portal_user, "Related field should be True")
        
        # Disable
        self.project.allow_portal_user = False
        self.assertFalse(self.task.allow_portal_user, "Related field should update")

    def test_default_value(self):
        """ Verify default is True """
        new_proj = self.env['project.project'].create({'name': 'New'})
        self.assertTrue(new_proj.allow_portal_user)
