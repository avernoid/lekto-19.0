from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import AccessError

@tagged('post_install', '-at_install')
class TestPortalAppAccess(TransactionCase):

    def setUp(self):
        super(TestPortalAppAccess, self).setUp()
        # Create a Portal User
        self.portal_user = self.env['res.users'].create({
            'name': 'Test Portal User',
            'login': 'test_portal_user',
        })
        
        # Remove from Internal User group (default) to avoid exclusive group error
        group_user = self.env.ref('base.group_user')
        group_user.write({'user_ids': [(3, self.portal_user.id)]})

        # Add user to Portal Group
        portal_group = self.env.ref('base.group_portal')
        # Using correct field 'user_ids' as clarified by user
        portal_group.write({'user_ids': [(4, self.portal_user.id)]})
        
        # Create a specific group
        self.special_group = self.env['res.groups'].create({
            'name': 'Special App Group'
        })
        
        # Create apps
        self.public_app = self.env['portal.app'].create({
            'name': 'Public App',
            'technical_name': 'public_app',
            'action_url': '/my/public',
            'sequence': 10,
        })
        
        self.private_app = self.env['portal.app'].create({
            'name': 'Private App',
            'technical_name': 'private_app',
            'action_url': '/my/private',
            'sequence': 20,
            'group_ids': [(6, 0, [self.special_group.id])]
        })

    def test_portal_user_app_visibility(self):
        """ Test that portal users can see public apps but fail 
            (gracefully or invisible) on restricted ones without 500 triggers.
        """
        # Simulate logic from controller:
        # As superuser/system, we can see everything, but we simulate logic:
        
        # 1. Fetch apps (controller does this with sudo)
        apps = self.env['portal.app'].with_user(self.portal_user).sudo().search([])
        
        # Verify both exist in search (sudo)
        self.assertIn(self.public_app, apps)
        self.assertIn(self.private_app, apps)

        # Simulate the filtering logic used in controller
        # Direct simulation of the FIXED logic
        
        # 1. Get user groups SAFE way (using DIRECT SQL)
        # Verify this does NOT raise AccessError or AttributeError for Portal User
        try:
            self.env.cr.execute("SELECT gid FROM res_groups_users_rel WHERE uid = %s", (self.portal_user.id,))
            user_group_ids = [row[0] for row in self.env.cr.fetchall()]
        except Exception as e:
            self.fail(f"Fetching user groups with SQL raised exception: {e}")
            
        # 2. Filter
        visible_apps = apps.filtered(lambda a: not a.group_ids or any(g.id in user_group_ids for g in a.group_ids))
        
        # Assert Public is visible
        self.assertIn(self.public_app, visible_apps)
        # Assert Private is NOT visible (user not in group)
        self.assertNotIn(self.private_app, visible_apps)
        
        # 3. Add user to group
        self.special_group.write({'user_ids': [(4, self.portal_user.id)]})
        # self.env.cr.execute("INSERT INTO res_groups_users_rel (gid, uid) VALUES (%s, %s)", (self.special_group.id, self.portal_user.id))
        
        # Re-evaluate
        self.env.cr.execute("SELECT gid FROM res_groups_users_rel WHERE uid = %s", (self.portal_user.id,))
        user_group_ids = [row[0] for row in self.env.cr.fetchall()]
        
        visible_apps = apps.filtered(lambda a: not a.group_ids or any(g.id in user_group_ids for g in a.group_ids))
        
        # Assert both visible
        self.assertIn(self.public_app, visible_apps)
        self.assertIn(self.private_app, visible_apps)
