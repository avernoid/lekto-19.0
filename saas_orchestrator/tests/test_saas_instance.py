from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

MOCK_PATH = 'odoo.addons.saas_orchestrator.models.saas_instance.requests.request'


def _make_response(data, status_code=200):
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = data
    mock_response.raise_for_status = MagicMock()
    return mock_response


@tagged('post_install', '-at_install')
class TestSaasInstanceActions(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('saas.orchestrator.url', 'http://test-api:8000')
        cls.env['ir.config_parameter'].sudo().set_param('saas.orchestrator.api_key', 'sk-test-key')

        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})
        cls.blueprint = cls.env['saas.product.blueprint'].create({
            'name': 'openclaw',
            'domain': 'orquestio.com',
        })
        cls.plan = cls.env['saas.product.plan'].create({
            'name': 'starter',
            'blueprint_id': cls.blueprint.id,
        })
        cls.tenant = cls.env['saas.tenant'].create({
            'name': 'tenant-001',
            'partner_id': cls.partner.id,
        })
        cls.instance = cls.env['saas.instance'].create({
            'name': 'inst-001',
            'tenant_id': cls.tenant.id,
            'plan_id': cls.plan.id,
            'state': 'draft',
        })

    def test_action_provision(self):
        api_data = {
            'instance_id': 'inst-001',
            'state': 'provisioning',
            'ec2_id': 'i-123',
            'ip_address': '10.0.0.1',
            'access_url': 'https://test.orquestio.com',
        }
        with patch(MOCK_PATH, return_value=_make_response(api_data)) as mock_req:
            self.instance.action_provision()
            mock_req.assert_called_once()
            call_args = mock_req.call_args
            self.assertEqual(call_args[0][0], 'POST')
            self.assertIn('/instances/create', call_args[0][1])
            payload = call_args[1]['json']
            self.assertEqual(payload['instance_id'], 'inst-001')
            self.assertEqual(payload['tenant_id'], 'tenant-001')
            self.assertEqual(payload['blueprint_name'], 'openclaw')
            self.assertEqual(payload['plan_id'], 'starter')

        self.assertEqual(self.instance.state, 'provisioning')
        self.assertEqual(self.instance.ec2_instance_id, 'i-123')
        self.assertEqual(self.instance.ip_address, '10.0.0.1')
        self.assertEqual(self.instance.access_url, 'https://test.orquestio.com')

    def test_action_provision_not_draft(self):
        self.instance.state = 'running'
        with self.assertRaises(UserError):
            self.instance.action_provision()

    def test_action_destroy(self):
        self.instance.state = 'running'
        with patch(MOCK_PATH, return_value=_make_response({})) as mock_req:
            self.instance.action_destroy()
            mock_req.assert_called_once()
        self.assertEqual(self.instance.state, 'destroying')

    def test_action_stop(self):
        self.instance.state = 'running'
        with patch(MOCK_PATH, return_value=_make_response({})):
            self.instance.action_stop()
        self.assertEqual(self.instance.state, 'stopped')

    def test_action_stop_not_running(self):
        self.instance.state = 'stopped'
        with self.assertRaises(UserError):
            self.instance.action_stop()

    def test_action_start(self):
        self.instance.state = 'stopped'
        with patch(MOCK_PATH, return_value=_make_response({})):
            self.instance.action_start()
        self.assertEqual(self.instance.state, 'running')

    def test_action_restart(self):
        self.instance.state = 'running'
        with patch(MOCK_PATH, return_value=_make_response({})):
            self.instance.action_restart()
        # No state change on restart, just no error
        self.assertEqual(self.instance.state, 'running')

    def test_api_call_missing_config(self):
        self.env['ir.config_parameter'].sudo().set_param('saas.orchestrator.url', '')
        self.env['ir.config_parameter'].sudo().set_param('saas.orchestrator.api_key', '')
        self.instance.state = 'running'
        with self.assertRaises(UserError):
            self.instance.action_stop()
        # Restore config for other tests
        self.env['ir.config_parameter'].sudo().set_param('saas.orchestrator.url', 'http://test-api:8000')
        self.env['ir.config_parameter'].sudo().set_param('saas.orchestrator.api_key', 'sk-test-key')


@tagged('post_install', '-at_install')
class TestSaasInstanceCrons(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('saas.orchestrator.url', 'http://test-api:8000')
        cls.env['ir.config_parameter'].sudo().set_param('saas.orchestrator.api_key', 'sk-test-key')

        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})
        cls.blueprint = cls.env['saas.product.blueprint'].create({
            'name': 'openclaw',
            'domain': 'orquestio.com',
        })
        cls.plan = cls.env['saas.product.plan'].create({
            'name': 'starter',
            'blueprint_id': cls.blueprint.id,
        })
        cls.tenant = cls.env['saas.tenant'].create({
            'name': 'tenant-002',
            'partner_id': cls.partner.id,
        })
        cls.instance = cls.env['saas.instance'].create({
            'name': 'inst-002',
            'tenant_id': cls.tenant.id,
            'plan_id': cls.plan.id,
            'state': 'running',
        })

    def test_cron_purge_by_max_records(self):
        self.plan.history_max_records = 2
        self.plan.history_retention_days = 0
        TaskHistory = self.env['saas.task.history']
        now = datetime.now()
        for i in range(5):
            TaskHistory.create({
                'instance_id': self.instance.id,
                'task_type': 'test',
                'created_at': now - timedelta(hours=5 - i),
            })
        with patch(MOCK_PATH, return_value=_make_response({})):
            self.env['saas.instance']._cron_purge_task_history()
        remaining = TaskHistory.search([('instance_id', '=', self.instance.id)])
        self.assertEqual(len(remaining), 2)
        # The 2 newest should remain
        dates = remaining.mapped('created_at')
        for d in dates:
            self.assertGreaterEqual(d, now - timedelta(hours=2))

    def test_cron_purge_by_retention_days(self):
        self.plan.history_retention_days = 7
        self.plan.history_max_records = 0
        TaskHistory = self.env['saas.task.history']
        # Delete any leftover records from other tests
        TaskHistory.search([('instance_id', '=', self.instance.id)]).unlink()

        now = datetime.now()
        # Old records (10 days ago)
        for i in range(3):
            TaskHistory.create({
                'instance_id': self.instance.id,
                'task_type': 'old',
                'created_at': now - timedelta(days=10, hours=i),
            })
        # Recent records (3 days ago)
        for i in range(2):
            TaskHistory.create({
                'instance_id': self.instance.id,
                'task_type': 'recent',
                'created_at': now - timedelta(days=3, hours=i),
            })

        with patch(MOCK_PATH, return_value=_make_response({})):
            self.env['saas.instance']._cron_purge_task_history()

        remaining = TaskHistory.search([('instance_id', '=', self.instance.id)])
        self.assertEqual(len(remaining), 2)
        for rec in remaining:
            self.assertEqual(rec.task_type, 'recent')
