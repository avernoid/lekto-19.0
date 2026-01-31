from odoo.tests.common import HttpCase, tagged
import json

@tagged('post_install', '-at_install')
class TestPartnerOfflineUI(HttpCase):

    def setUp(self):
        super().setUp()
        # 1. Create Portal User following DEV_GUIDELINES
        self.portal_user = self.env['res.users'].create({
            'name': 'Test Offline Portal',
            'login': 'offline_portal_test',
            'password': 'portal_password',
            'group_ids': [(6, 0, [])]  # Start empty
        })
        
        # Remove Internal, Add Portal (Pattern form DEV_GUIDELINES)
        self.env.ref('base.group_user').write({'user_ids': [(3, self.portal_user.id)]})
        self.env.ref('base.group_portal').write({'user_ids': [(4, self.portal_user.id)]})

        # Add "View All" permission to see search results (New Visibility Rules)
        self.env.ref('partner_offline.group_portal_all').write({'user_ids': [(4, self.portal_user.id)]})
        
        # Create some dummy partners for search
        self.env['res.partner'].create({'name': 'OfflineTest Partner A', 'phone': '123456789'})
        self.env['res.partner'].create({'name': 'OfflineTest Partner B', 'phone': '987654321'})

    def test_access_rights(self):
        """ Test Access Rights: Public vs Portal """
        # 1. Public User -> Should Redirect to Login or 403 (depending on auth='user')
        # Our controller is auth='user', so it should redirect to login
        response = self.url_open('/my/partners')
        self.assertTrue(
            '/web/login' in response.url or response.status_code in [403], 
            "Public user should not access /my/partners"
        )
        
        # 2. Portal User -> Should Access 200 OK
        self.authenticate('offline_portal_test', 'portal_password')
        response = self.url_open('/my/partners')
        self.assertEqual(response.status_code, 200, "Portal user must access /my/partners")
        
    def test_pwa_manifest(self):
        """ Test PWA Manifest Access and Scope """
        self.authenticate('offline_portal_test', 'portal_password')
        
        response = self.url_open('/partner_offline/manifest.json')
        self.assertEqual(response.status_code, 200, "Manifest should be accessible")
        
        manifest = json.loads(response.content)
        self.assertIn('name', manifest, "Manifest must have a name")
        # Ensure scope is standard or valid
        self.assertTrue(manifest.get('scope', '').startswith('/'), "Scope must be a path")

    def test_search_robustness(self):
        """ Test Search Controller with unexpected inputs (500 avoidance) """
        self.authenticate('offline_portal_test', 'portal_password')
        
        # 1. Empty Search
        response = self.url_open('/my/partners?search=')
        self.assertEqual(response.status_code, 200, "Empty search should not crash")
        
        # 2. Special Characters
        response = self.url_open('/my/partners?search=$$%invalid%')
        self.assertEqual(response.status_code, 200, "Search with special chars should not crash")
        
        # 3. Standard Search
        response = self.url_open('/my/partners?search=OfflineTest')
        self.assertEqual(response.status_code, 200, "Normal search should work")
        self.assertIn(b'OfflineTest Partner A', response.content, "Search result should be present")

    def test_detail_view_no_address(self):
        """ PROOF OF FIX: Test Detail View for Partner with NO Address (Regression Test for 500 Error) """
        self.authenticate('offline_portal_test', 'portal_password')
        
        # Create partner with NO address
        empty_partner = self.env['res.partner'].create({
            'name': 'No Address Partner',
            'street': False,
            'city': False,
            'country_id': False
        })
        
        # Access Detail View
        response = self.url_open('/my/partners/%s' % empty_partner.id)
        self.assertEqual(response.status_code, 200, "Detail view should NOT crash (500) even if address is missing")
        self.assertIn(b'No Address Partner', response.content, "Should render partner name")
