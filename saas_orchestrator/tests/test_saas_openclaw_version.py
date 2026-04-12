from unittest.mock import MagicMock, patch

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

MOCK_REQUESTS_GET = 'odoo.addons.saas_orchestrator.models.saas_openclaw_version.requests.get'


def _make_response(data, status_code=200):
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = data
    mock_response.raise_for_status = MagicMock()
    return mock_response


@tagged('post_install', '-at_install')
class TestSaasOpenclawVersion(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('saas.orchestrator.url', 'http://test-api:8000')
        cls.env['ir.config_parameter'].sudo().set_param('saas.orchestrator.api_key', 'sk-test-key')

    def test_create_version(self):
        version = self.env['saas.openclaw.version'].create({
            'name': 'v2026.4.10',
            'upstream_tag': 'v2026.4.10',
            'built_at': '2026-04-10 00:00:00',
            'status': 'ok',
        })
        self.assertEqual(version.name, 'v2026.4.10')
        self.assertEqual(version.status, 'ok')

    def test_cron_sync_creates_new_versions(self):
        api_data = {
            'items': [
                {
                    'tag': 'v2026.4.10',
                    'upstream_tag': 'v2026.4.10',
                    'built_at': '2026-04-10 00:00:00+00:00',
                    'promoted_to_stable': '2026-04-10 00:00:00+00:00',
                    'status': 'ok',
                    'notes': 'Initial version',
                    'release_notes_url': None,
                },
                {
                    'tag': 'v2026.4.15',
                    'upstream_tag': 'v2026.4.15',
                    'built_at': '2026-04-15 00:00:00+00:00',
                    'promoted_to_stable': None,
                    'status': 'ok',
                    'notes': 'New version',
                    'release_notes_url': None,
                },
            ],
            'total': 2,
        }
        with patch(MOCK_REQUESTS_GET, return_value=_make_response(api_data)):
            self.env['saas.openclaw.version']._cron_sync_versions()

        versions = self.env['saas.openclaw.version'].search([])
        tags = versions.mapped('name')
        self.assertIn('v2026.4.10', tags)
        self.assertIn('v2026.4.15', tags)

    def test_cron_sync_marks_removed_versions_inactive(self):
        # Create a version that won't be in the API response
        self.env['saas.openclaw.version'].create({
            'name': 'v2026.3.01',
            'upstream_tag': 'v2026.3.01',
            'built_at': '2026-03-01 00:00:00',
            'status': 'ok',
        })
        api_data = {
            'items': [
                {
                    'tag': 'v2026.4.10',
                    'upstream_tag': 'v2026.4.10',
                    'built_at': '2026-04-10 00:00:00+00:00',
                    'status': 'ok',
                },
            ],
            'total': 1,
        }
        with patch(MOCK_REQUESTS_GET, return_value=_make_response(api_data)):
            self.env['saas.openclaw.version']._cron_sync_versions()

        stale = self.env['saas.openclaw.version'].with_context(active_test=False).search([
            ('name', '=', 'v2026.3.01'),
        ])
        self.assertFalse(stale.active)

    def test_cron_sync_updates_existing_version(self):
        self.env['saas.openclaw.version'].create({
            'name': 'v2026.4.10',
            'upstream_tag': 'v2026.4.10',
            'built_at': '2026-04-10 00:00:00',
            'status': 'ok',
            'notes': 'old notes',
        })
        api_data = {
            'items': [
                {
                    'tag': 'v2026.4.10',
                    'upstream_tag': 'v2026.4.10',
                    'built_at': '2026-04-10 00:00:00+00:00',
                    'status': 'broken',
                    'notes': 'has a bug',
                },
            ],
            'total': 1,
        }
        with patch(MOCK_REQUESTS_GET, return_value=_make_response(api_data)):
            self.env['saas.openclaw.version']._cron_sync_versions()

        version = self.env['saas.openclaw.version'].search([('name', '=', 'v2026.4.10')])
        self.assertEqual(version.status, 'broken')
        self.assertEqual(version.notes, 'has a bug')

    @mute_logger('odoo.addons.saas_orchestrator.models.saas_openclaw_version')
    def test_cron_sync_no_config_skips(self):
        """Sync does nothing if orchestrator URL is not configured."""
        self.env['ir.config_parameter'].sudo().set_param('saas.orchestrator.url', '')
        with patch(MOCK_REQUESTS_GET) as mock_get:
            self.env['saas.openclaw.version']._cron_sync_versions()
            mock_get.assert_not_called()
        # Restore
        self.env['ir.config_parameter'].sudo().set_param('saas.orchestrator.url', 'http://test-api:8000')


@tagged('post_install', '-at_install')
class TestInstanceVersionRefresh(TransactionCase):
    """Test that action_refresh syncs current_version from orchestrator."""

    MOCK_REQUEST = 'odoo.addons.saas_orchestrator.models.saas_instance.requests.request'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('saas.orchestrator.url', 'http://test-api:8000')
        cls.env['ir.config_parameter'].sudo().set_param('saas.orchestrator.api_key', 'sk-test-key')
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})
        cls.blueprint = cls.env['saas.product.blueprint'].create({
            'name': 'openclaw-vtest',
            'domain': 'test.com',
        })
        cls.plan = cls.env['saas.product.plan'].create({
            'name': 'basic',
            'blueprint_id': cls.blueprint.id,
        })
        cls.tenant = cls.env['saas.tenant'].create({
            'name': 'tenant-vtest',
            'partner_id': cls.partner.id,
        })
        cls.version = cls.env['saas.openclaw.version'].create({
            'name': 'v2026.4.10',
            'upstream_tag': 'v2026.4.10',
            'built_at': '2026-04-10 00:00:00',
            'status': 'ok',
        })
        cls.instance = cls.env['saas.instance'].create({
            'name': 'inst-vtest-001',
            'tenant_id': cls.tenant.id,
            'plan_id': cls.plan.id,
            'state': 'running',
        })

    def test_refresh_syncs_current_version(self):
        api_data = {
            'instance_id': 'inst-vtest-001',
            'state': 'running',
            'current_version': 'v2026.4.10',
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = api_data
        mock_resp.raise_for_status = MagicMock()

        with patch(self.MOCK_REQUEST, return_value=mock_resp):
            self.instance.action_refresh()

        self.assertEqual(self.instance.current_version_id, self.version)

    def test_refresh_without_version_leaves_field_empty(self):
        api_data = {
            'instance_id': 'inst-vtest-001',
            'state': 'running',
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = api_data
        mock_resp.raise_for_status = MagicMock()

        with patch(self.MOCK_REQUEST, return_value=mock_resp):
            self.instance.action_refresh()

        self.assertFalse(self.instance.current_version_id)
