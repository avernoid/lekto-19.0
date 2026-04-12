from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

MOCK_PATH = 'odoo.addons.saas_orchestrator.models.saas_instance.requests.request'


def _make_response(data, status_code=200):
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = data
    mock_response.raise_for_status = MagicMock()
    return mock_response


@tagged('post_install', '-at_install')
class TestSaasInstanceRefresh(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('saas.orchestrator.url', 'http://test-api:8000')
        cls.env['ir.config_parameter'].sudo().set_param('saas.orchestrator.api_key', 'sk-test-key')

        cls.partner = cls.env['res.partner'].create({'name': 'Refresh Partner'})
        cls.blueprint = cls.env['saas.product.blueprint'].create({
            'name': 'openclaw',
            'domain': 'orquestio.com',
        })
        cls.plan = cls.env['saas.product.plan'].create({
            'name': 'starter',
            'blueprint_id': cls.blueprint.id,
        })
        cls.tenant = cls.env['saas.tenant'].create({
            'name': 'tenant-refresh',
            'partner_id': cls.partner.id,
        })

    def _make_instance(self, name, state='running'):
        return self.env['saas.instance'].create({
            'name': name,
            'tenant_id': self.tenant.id,
            'plan_id': self.plan.id,
            'state': state,
        })

    def test_action_refresh_single_happy_path(self):
        instance = self._make_instance('inst-refresh-1')
        api_data = {
            'state': 'running',
            'ec2_id': 'i-789',
            'ip_address': '10.0.0.9',
            'access_url': 'https://refresh.orquestio.com',
            'cpu_usage': 42.5,
            'ram_usage': 55.0,
            'disk_usage': 12.3,
            'last_health_check': '2026-04-11T10:00:00',
        }
        with patch(MOCK_PATH, return_value=_make_response(api_data)) as mock_req:
            result = instance.action_refresh()
            mock_req.assert_called_once()
            call_args = mock_req.call_args
            self.assertEqual(call_args[0][0], 'GET')
            self.assertIn('/instances/inst-refresh-1/status', call_args[0][1])

        self.assertTrue(result)
        self.assertEqual(instance.ec2_instance_id, 'i-789')
        self.assertEqual(instance.ip_address, '10.0.0.9')
        self.assertEqual(instance.access_url, 'https://refresh.orquestio.com')
        self.assertEqual(instance.cpu_usage, 42.5)
        self.assertEqual(instance.ram_usage, 55.0)
        self.assertEqual(instance.disk_usage, 12.3)
        self.assertTrue(instance.last_state_fetch_at, "last_state_fetch_at should be set")
        self.assertTrue(instance.last_health_check, "last_health_check should be set")

    @mute_logger('odoo.addons.saas_orchestrator.models.saas_instance')
    def test_action_refresh_single_failure_raises(self):
        instance = self._make_instance('inst-refresh-2')
        with patch(MOCK_PATH, side_effect=Exception("Connection refused")):
            with self.assertRaises(UserError):
                instance.action_refresh()

    def test_action_refresh_bulk_happy_path(self):
        instances = self.env['saas.instance']
        for i in range(3):
            instances |= self._make_instance(f'inst-bulk-{i}')
        api_data = {
            'state': 'running',
            'ec2_id': 'i-bulk',
            'ip_address': '10.0.1.1',
            'access_url': 'https://bulk.orquestio.com',
        }
        with patch(MOCK_PATH, return_value=_make_response(api_data)):
            result = instances.action_refresh()

        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('type'), 'ir.actions.client')
        self.assertEqual(result.get('tag'), 'display_notification')
        self.assertEqual(result['params']['type'], 'success')
        self.assertIn('3', result['params']['message'])
        for inst in instances:
            self.assertEqual(inst.ec2_instance_id, 'i-bulk')
            self.assertTrue(inst.last_state_fetch_at)

    @mute_logger('odoo.addons.saas_orchestrator.models.saas_instance')
    def test_action_refresh_bulk_partial_failure(self):
        inst_a = self._make_instance('inst-partial-a')
        inst_b = self._make_instance('inst-partial-b')
        inst_c = self._make_instance('inst-partial-c')
        instances = inst_a | inst_b | inst_c

        good_response = _make_response({
            'state': 'running',
            'ec2_id': 'i-ok',
            'ip_address': '10.0.2.1',
            'access_url': 'https://ok.orquestio.com',
        })

        call_count = {'n': 0}

        def side_effect(*args, **kwargs):
            call_count['n'] += 1
            if call_count['n'] == 2:
                raise Exception("Boom")
            return good_response

        with patch(MOCK_PATH, side_effect=side_effect):
            result = instances.action_refresh()

        self.assertEqual(result['params']['type'], 'warning')
        # The failed instance is inst_b (the second one in recordset order)
        self.assertIn(inst_b.name, result['params']['message'])
        # The other two should have been updated
        self.assertEqual(inst_a.ec2_instance_id, 'i-ok')
        self.assertEqual(inst_c.ec2_instance_id, 'i-ok')

    def test_action_refresh_bulk_over_limit(self):
        instances = self.env['saas.instance']
        for i in range(51):
            instances |= self._make_instance(f'inst-limit-{i}')
        with self.assertRaises(UserError) as cm:
            instances.action_refresh()
        self.assertIn('50', str(cm.exception))

    def test_cron_sync_method_removed(self):
        self.assertFalse(
            hasattr(type(self.env['saas.instance']), '_cron_sync_instance_status'),
            "_cron_sync_instance_status should have been removed from the model",
        )
