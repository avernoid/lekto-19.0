from unittest.mock import MagicMock, patch

import requests

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
class TestSaasOperationUpgradeWizard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param(
            'saas.orchestrator.url', 'http://test-api:8000',
        )
        cls.env['ir.config_parameter'].sudo().set_param(
            'saas.orchestrator.api_key', 'sk-test-key',
        )

        cls.partner = cls.env['res.partner'].create({'name': 'Upgrade Partner'})
        cls.blueprint = cls.env['saas.product.blueprint'].create({
            'name': 'openclaw',
            'domain': 'orquestio.com',
        })
        cls.blueprint_empty = cls.env['saas.product.blueprint'].create({
            'name': 'empty-bp',
            'domain': 'orquestio.com',
        })
        cls.operation = cls.env['saas.product.operation'].create({
            'blueprint_id': cls.blueprint.id,
            'code': 'upgrade',
            'label': 'Upgrade',
            'script_path': '/opt/orquestio/scripts/upgrade.sh',
            'timeout_seconds': 600,
        })
        cls.plan = cls.env['saas.product.plan'].create({
            'name': 'starter',
            'blueprint_id': cls.blueprint.id,
        })
        cls.plan_empty = cls.env['saas.product.plan'].create({
            'name': 'starter-empty',
            'blueprint_id': cls.blueprint_empty.id,
        })
        cls.tenant = cls.env['saas.tenant'].create({
            'name': 'tenant-upgrade',
            'partner_id': cls.partner.id,
        })

    def _make_instance(self, name, plan=None, state='running'):
        return self.env['saas.instance'].create({
            'name': name,
            'tenant_id': self.tenant.id,
            'plan_id': (plan or self.plan).id,
            'state': state,
        })

    # ------------------------------------------------------------------
    # Computed field + action opener
    # ------------------------------------------------------------------

    def test_has_upgrade_operation_computed_true(self):
        instance = self._make_instance('inst-upg-1')
        self.assertTrue(instance.has_upgrade_operation)

    def test_has_upgrade_operation_computed_false(self):
        instance = self._make_instance('inst-upg-2', plan=self.plan_empty)
        self.assertFalse(instance.has_upgrade_operation)

    def test_action_open_upgrade_wizard_returns_action(self):
        instance = self._make_instance('inst-upg-3')
        result = instance.action_open_upgrade_wizard()
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('res_model'), 'saas.operation.upgrade.wizard')
        self.assertEqual(result.get('target'), 'new')
        self.assertEqual(
            result.get('context', {}).get('default_instance_id'), instance.id,
        )

    def test_action_open_upgrade_wizard_raises_without_operation(self):
        instance = self._make_instance('inst-upg-4', plan=self.plan_empty)
        with self.assertRaises(UserError):
            instance.action_open_upgrade_wizard()

    # ------------------------------------------------------------------
    # Wizard action_run
    # ------------------------------------------------------------------

    def _make_wizard(self, instance, target_version='v2026.4.11'):
        return self.env['saas.operation.upgrade.wizard'].create({
            'instance_id': instance.id,
            'target_version': target_version,
        })

    def test_action_run_builds_correct_payload(self):
        instance = self._make_instance('inst-upg-run-1')
        wizard = self._make_wizard(instance, target_version='v2026.4.11')
        task_response = _make_response({'task_id': 'task-abc-123'})
        status_response = _make_response({'state': 'running'})

        with patch(MOCK_PATH, side_effect=[task_response, status_response]) as mock_req:
            wizard.action_run()
            # First call: POST /instances/<name>/tasks
            first_call = mock_req.call_args_list[0]
            self.assertEqual(first_call[0][0], 'POST')
            self.assertIn(f'/instances/{instance.name}/tasks', first_call[0][1])
            sent_payload = first_call[1]['json']
            self.assertEqual(sent_payload['operation_code'], 'upgrade')
            self.assertEqual(
                sent_payload['script_path'],
                '/opt/orquestio/scripts/upgrade.sh',
            )
            self.assertEqual(sent_payload['script_args'], ['v2026.4.11'])
            self.assertEqual(sent_payload['timeout_seconds'], 600)
            self.assertIn('idempotency_key', sent_payload)

    def test_action_run_creates_task_history_row(self):
        instance = self._make_instance('inst-upg-run-2')
        wizard = self._make_wizard(instance)
        task_response = _make_response({'task_id': 'task-xyz-999'})
        status_response = _make_response({'state': 'running'})

        with patch(MOCK_PATH, side_effect=[task_response, status_response]):
            wizard.action_run()

        history = self.env['saas.task.history'].search(
            [('instance_id', '=', instance.id)],
        )
        self.assertEqual(len(history), 1)
        self.assertEqual(history.orchestrator_task_id, 'task-xyz-999')
        self.assertEqual(history.state, 'in_progress')
        self.assertEqual(history.operation_id, self.operation)

    @mute_logger('odoo.addons.saas_orchestrator.models.saas_instance')
    def test_action_run_raises_if_no_operation_in_catalog(self):
        instance = self._make_instance('inst-upg-run-3', plan=self.plan_empty)
        # Wizard creation bypasses the has_upgrade_operation check because it's
        # a transient model, but action_run must raise.
        wizard = self._make_wizard(instance)
        with self.assertRaises(UserError):
            wizard.action_run()

    @mute_logger('odoo.addons.saas_orchestrator.models.saas_instance')
    def test_action_run_http_error_propagates_as_user_error(self):
        instance = self._make_instance('inst-upg-run-4')
        wizard = self._make_wizard(instance)
        with patch(
            MOCK_PATH,
            side_effect=requests.exceptions.ConnectionError("Boom"),
        ):
            with self.assertRaises(UserError):
                wizard.action_run()

    def test_action_run_returns_close_action(self):
        instance = self._make_instance('inst-upg-run-5')
        wizard = self._make_wizard(instance)
        task_response = _make_response({'task_id': 'task-close-1'})
        status_response = _make_response({'state': 'running'})
        with patch(MOCK_PATH, side_effect=[task_response, status_response]):
            result = wizard.action_run()
        self.assertEqual(result.get('type'), 'ir.actions.act_window_close')

    # ------------------------------------------------------------------
    # Deuda #8 — target_version validator extracts the tag from full image refs
    # ------------------------------------------------------------------

    def test_extract_tag_bare_tag(self):
        from odoo.addons.saas_orchestrator.wizard.saas_operation_upgrade_wizard \
            import SaasOperationUpgradeWizard
        self.assertEqual(SaasOperationUpgradeWizard._extract_tag('v2026.4.11'), 'v2026.4.11')

    def test_extract_tag_full_image_ref(self):
        from odoo.addons.saas_orchestrator.wizard.saas_operation_upgrade_wizard \
            import SaasOperationUpgradeWizard
        self.assertEqual(
            SaasOperationUpgradeWizard._extract_tag('odoopartners/openclaw:v2026.4.11'),
            'v2026.4.11',
        )

    def test_extract_tag_with_registry_prefix(self):
        from odoo.addons.saas_orchestrator.wizard.saas_operation_upgrade_wizard \
            import SaasOperationUpgradeWizard
        self.assertEqual(
            SaasOperationUpgradeWizard._extract_tag('registry.example.com/foo/bar:v9.9.9'),
            'v9.9.9',
        )

    def test_extract_tag_strips_whitespace(self):
        from odoo.addons.saas_orchestrator.wizard.saas_operation_upgrade_wizard \
            import SaasOperationUpgradeWizard
        self.assertEqual(SaasOperationUpgradeWizard._extract_tag('  v2026.4.11  '), 'v2026.4.11')

    def test_extract_tag_empty_raises(self):
        from odoo.addons.saas_orchestrator.wizard.saas_operation_upgrade_wizard \
            import SaasOperationUpgradeWizard
        with self.assertRaises(UserError):
            SaasOperationUpgradeWizard._extract_tag('')

    def test_action_run_dispatches_with_extracted_tag(self):
        """Full image refs are sanitized before being sent to the orchestrator."""
        instance = self._make_instance('inst-upg-tag-1')
        wizard = self._make_wizard(
            instance, target_version='odoopartners/openclaw:v2026.4.99',
        )
        task_response = _make_response({'task_id': 'task-tag-1'})
        status_response = _make_response({'state': 'running'})
        with patch(MOCK_PATH, side_effect=[task_response, status_response]) as mock_req:
            wizard.action_run()
        sent = mock_req.call_args_list[0][1]['json']
        # Bug deuda #8: pre-fix would have sent the full image ref here.
        self.assertEqual(sent['script_args'], ['v2026.4.99'])
