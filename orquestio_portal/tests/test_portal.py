from unittest.mock import MagicMock, patch

from odoo.tests import tagged
from odoo.tests.common import HttpCase

MOCK_PATH = 'odoo.addons.saas_orchestrator.models.saas_instance.requests.request'


def _make_response(data=None, status_code=200):
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = data or {}
    mock_response.raise_for_status = MagicMock()
    return mock_response


@tagged('post_install', '-at_install')
class TestSaasPortal(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # API config
        cls.env['ir.config_parameter'].sudo().set_param('saas.orchestrator.url', 'http://test-api:8000')
        cls.env['ir.config_parameter'].sudo().set_param('saas.orchestrator.api_key', 'sk-test-key')

        # Portal user (Group Cleanup pattern)
        cls.portal_user = cls.env['res.users'].create({
            'name': 'Test Portal',
            'login': 'test_portal_saas',
            'password': 'test_portal_saas',
        })
        cls.env.ref('base.group_user').write({'user_ids': [(3, cls.portal_user.id)]})
        cls.env.ref('base.group_portal').write({'user_ids': [(4, cls.portal_user.id)]})

        cls.partner = cls.portal_user.partner_id

        cls.blueprint = cls.env['saas.product.blueprint'].create({
            'name': 'openclaw',
            'domain': 'orquestio.com',
        })
        cls.plan = cls.env['saas.product.plan'].create({
            'name': 'starter',
            'blueprint_id': cls.blueprint.id,
            'env_vars_included': 5,
        })
        cls.tenant = cls.env['saas.tenant'].create({
            'name': 'portal-tenant-001',
            'partner_id': cls.partner.id,
        })
        cls.instance = cls.env['saas.instance'].create({
            'name': 'portal-inst-001',
            'tenant_id': cls.tenant.id,
            'plan_id': cls.plan.id,
            'state': 'running',
        })

        # Second user (for access control tests)
        cls.other_user = cls.env['res.users'].create({
            'name': 'Other Portal',
            'login': 'test_portal_other',
            'password': 'test_portal_other',
        })
        cls.env.ref('base.group_user').write({'user_ids': [(3, cls.other_user.id)]})
        cls.env.ref('base.group_portal').write({'user_ids': [(4, cls.other_user.id)]})

        cls.other_partner = cls.other_user.partner_id
        cls.other_tenant = cls.env['saas.tenant'].create({
            'name': 'portal-tenant-002',
            'partner_id': cls.other_partner.id,
        })
        cls.other_instance = cls.env['saas.instance'].create({
            'name': 'portal-inst-002',
            'tenant_id': cls.other_tenant.id,
            'plan_id': cls.plan.id,
            'state': 'running',
        })

    def test_portal_instance_list(self):
        """Portal user can see their own instances."""
        self.authenticate('test_portal_saas', 'test_portal_saas')
        response = self.url_open('/my/instances')
        self.assertEqual(response.status_code, 200)
        self.assertIn('portal-inst-001', response.text)

    def test_portal_instance_detail(self):
        """Portal user can view detail of their own instance."""
        self.authenticate('test_portal_saas', 'test_portal_saas')
        response = self.url_open(f'/my/instances/{self.instance.id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn('portal-inst-001', response.text)

    def test_portal_instance_detail_other_user(self):
        """Portal user cannot access another user's instance."""
        self.authenticate('test_portal_saas', 'test_portal_saas')
        response = self.url_open(f'/my/instances/{self.other_instance.id}', allow_redirects=False)
        # Should redirect to /my/instances (302) since ownership check fails
        if response.status_code == 302:
            self.assertIn('/my/instances', response.headers.get('Location', ''))
        else:
            # If redirect was followed, the other instance name should not appear
            self.assertNotIn('portal-inst-002', response.text)

    def _get_csrf_token(self):
        """Get a valid CSRF token by loading a page first."""
        response = self.url_open('/my')
        # Extract csrf_token from the page
        import re
        match = re.search(r'csrf_token.*?value="([^"]+)"', response.text)
        if match:
            return match.group(1)
        # Fallback: use odoo.http module
        from odoo.http import Request
        return Request.csrf_token(self)

    def test_portal_restart(self):
        """Portal user can restart their own instance."""
        self.authenticate('test_portal_saas', 'test_portal_saas')
        csrf = self._get_csrf_token()
        with patch(MOCK_PATH, return_value=_make_response()):
            response = self.url_open(
                f'/my/instances/{self.instance.id}/restart',
                data={'csrf_token': csrf},
                allow_redirects=False,
            )
        self.assertIn(response.status_code, (200, 302, 303))

    def test_portal_add_env_var(self):
        """Portal user can add an environment variable."""
        self.authenticate('test_portal_saas', 'test_portal_saas')
        csrf = self._get_csrf_token()
        response = self.url_open(
            f'/my/instances/{self.instance.id}/env-vars',
            data={'name': 'TEST_VAR', 'value': 'test_value', 'csrf_token': csrf},
            allow_redirects=False,
        )
        self.assertIn(response.status_code, (200, 302, 303))
        env_var = self.env['saas.instance.env.var'].sudo().search([
            ('instance_id', '=', self.instance.id),
            ('name', '=', 'TEST_VAR'),
        ])
        self.assertTrue(env_var.exists())
        env_var.unlink()

    def test_portal_add_env_var_limit(self):
        """Portal user cannot exceed the plan's env var limit."""
        self.authenticate('test_portal_saas', 'test_portal_saas')
        csrf = self._get_csrf_token()
        self.plan.env_vars_included = 1
        existing = self.env['saas.instance.env.var'].sudo().create({
            'instance_id': self.instance.id,
            'name': 'EXISTING_VAR',
            'value': 'existing',
        })
        try:
            response = self.url_open(
                f'/my/instances/{self.instance.id}/env-vars',
                data={'name': 'OVER_LIMIT', 'value': 'nope', 'csrf_token': csrf},
                allow_redirects=False,
            )
            self.assertIn(response.status_code, (200, 302, 303))
            over = self.env['saas.instance.env.var'].sudo().search([
                ('instance_id', '=', self.instance.id),
                ('name', '=', 'OVER_LIMIT'),
            ])
            self.assertFalse(over.exists())
        finally:
            existing.unlink()
            self.plan.env_vars_included = 5

    def test_portal_delete_env_var(self):
        """Portal user can delete an environment variable."""
        self.authenticate('test_portal_saas', 'test_portal_saas')
        csrf = self._get_csrf_token()
        env_var = self.env['saas.instance.env.var'].sudo().create({
            'instance_id': self.instance.id,
            'name': 'TO_DELETE',
            'value': 'bye',
        })
        response = self.url_open(
            f'/my/instances/{self.instance.id}/env-vars/{env_var.id}/delete',
            data={'csrf_token': csrf},
            allow_redirects=False,
        )
        self.assertIn(response.status_code, (200, 302, 303))
        self.assertFalse(env_var.exists())
