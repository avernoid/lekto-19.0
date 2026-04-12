from unittest.mock import MagicMock, patch
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

MOCK_PATH = 'odoo.addons.saas_orchestrator.models.res_config_settings.requests.get'


@tagged('post_install', '-at_install')
class TestResConfigSettings(TransactionCase):

    def _make_response(self, data, status_code=200):
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_response.json.return_value = data
        mock_response.raise_for_status = MagicMock()
        return mock_response

    def test_settings_persist_to_system_parameters(self):
        """Setting the fields in res.config.settings writes to ir.config_parameter."""
        settings = self.env['res.config.settings'].create({
            'saas_orchestrator_url': 'https://api.test.example.com',
            'saas_orchestrator_api_key': 'sk-orch-test-123',
        })
        settings.execute()
        ICP = self.env['ir.config_parameter'].sudo()
        self.assertEqual(ICP.get_param('saas.orchestrator.url'), 'https://api.test.example.com')
        self.assertEqual(ICP.get_param('saas.orchestrator.api_key'), 'sk-orch-test-123')

    def test_test_connection_success(self):
        """action_test_orchestrator_connection returns success notification when /health returns healthy."""
        settings = self.env['res.config.settings'].create({
            'saas_orchestrator_url': 'https://api.test.example.com',
            'saas_orchestrator_api_key': 'sk-orch-test-123',
        })
        with patch(MOCK_PATH, return_value=self._make_response({
            'status': 'healthy',
            'checks': {'api': 'ok', 'database': 'ok', 'redis': 'ok'},
        })):
            result = settings.action_test_orchestrator_connection()
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'display_notification')
        self.assertEqual(result['params']['type'], 'success')

    def test_test_connection_url_missing(self):
        """action_test_orchestrator_connection raises if URL is empty."""
        settings = self.env['res.config.settings'].create({
            'saas_orchestrator_url': '',
            'saas_orchestrator_api_key': 'sk-orch-test',
        })
        with self.assertRaises(UserError):
            settings.action_test_orchestrator_connection()

    def test_test_connection_connection_error(self):
        """action_test_orchestrator_connection raises UserError on ConnectionError."""
        import requests as req_module
        settings = self.env['res.config.settings'].create({
            'saas_orchestrator_url': 'https://api.unreachable.example.com',
            'saas_orchestrator_api_key': 'sk-orch-test',
        })
        with patch(MOCK_PATH, side_effect=req_module.exceptions.ConnectionError("refused")):
            with self.assertRaises(UserError):
                settings.action_test_orchestrator_connection()
