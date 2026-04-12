"""
Tests for the Sprint 3 operation wizards: restart, rotate_password, update_env_var.

Mirrors the structure of test_saas_operation_upgrade_wizard.py — same fixtures,
same _make_response helper, same MOCK_PATH for stubbing requests, same
mute_logger pattern around expected error paths. Adds wizard-specific tests
for the validators (rotate_password.confirmed flag, update_env_var.var_name
regex).
"""

from unittest.mock import MagicMock, patch

import requests

from odoo.exceptions import UserError, ValidationError
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
class _Sprint3WizardBase(TransactionCase):
    """Shared fixture: blueprint with all 3 ops + an empty blueprint without."""

    OP_CODES = ('restart', 'rotate_password', 'update_env_var')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param(
            'saas.orchestrator.url', 'http://test-api:8000',
        )
        cls.env['ir.config_parameter'].sudo().set_param(
            'saas.orchestrator.api_key', 'sk-test-key',
        )

        cls.partner = cls.env['res.partner'].create({'name': 'Sprint3 Partner'})
        cls.blueprint = cls.env['saas.product.blueprint'].create({
            'name': 'sprint3-bp',
            'domain': 'orquestio.com',
        })
        cls.blueprint_empty = cls.env['saas.product.blueprint'].create({
            'name': 'sprint3-empty-bp',
            'domain': 'orquestio.com',
        })
        cls.ops_by_code = {}
        for code in cls.OP_CODES:
            op = cls.env['saas.product.operation'].create({
                'blueprint_id': cls.blueprint.id,
                'code': code,
                'label': code.replace('_', ' ').title(),
                'script_path': f'/opt/openclaw/scripts/{code}.sh',
                'timeout_seconds': 120,
            })
            cls.ops_by_code[code] = op

        cls.plan = cls.env['saas.product.plan'].create({
            'name': 'sprint3-starter',
            'blueprint_id': cls.blueprint.id,
        })
        cls.plan_empty = cls.env['saas.product.plan'].create({
            'name': 'sprint3-starter-empty',
            'blueprint_id': cls.blueprint_empty.id,
        })
        cls.tenant = cls.env['saas.tenant'].create({
            'name': 'sprint3-tenant',
            'partner_id': cls.partner.id,
        })

    def _make_instance(self, name, plan=None, state='running'):
        return self.env['saas.instance'].create({
            'name': name,
            'tenant_id': self.tenant.id,
            'plan_id': (plan or self.plan).id,
            'state': state,
        })


# =============================================================================
# Restart wizard
# =============================================================================
class TestSaasOperationRestartWizard(_Sprint3WizardBase):

    def test_has_restart_operation_computed_true(self):
        instance = self._make_instance('inst-rs-1')
        self.assertTrue(instance.has_restart_operation)

    def test_has_restart_operation_computed_false(self):
        instance = self._make_instance('inst-rs-2', plan=self.plan_empty)
        self.assertFalse(instance.has_restart_operation)

    def test_action_open_restart_wizard_returns_action(self):
        instance = self._make_instance('inst-rs-3')
        result = instance.action_open_restart_wizard()
        self.assertEqual(result.get('res_model'), 'saas.operation.restart.wizard')
        self.assertEqual(result.get('target'), 'new')
        self.assertEqual(
            result.get('context', {}).get('default_instance_id'), instance.id,
        )

    def test_action_open_restart_wizard_raises_without_operation(self):
        instance = self._make_instance('inst-rs-4', plan=self.plan_empty)
        with self.assertRaises(UserError):
            instance.action_open_restart_wizard()

    def _make_wizard(self, instance):
        return self.env['saas.operation.restart.wizard'].create({
            'instance_id': instance.id,
        })

    def test_action_run_builds_payload_with_no_args(self):
        instance = self._make_instance('inst-rs-run-1')
        wizard = self._make_wizard(instance)
        task = _make_response({'task_id': 'task-rs-1'})
        status = _make_response({'state': 'running'})
        with patch(MOCK_PATH, side_effect=[task, status]) as mock_req:
            wizard.action_run()
        sent = mock_req.call_args_list[0][1]['json']
        self.assertEqual(sent['operation_code'], 'restart')
        self.assertEqual(sent['script_path'], '/opt/openclaw/scripts/restart.sh')
        self.assertEqual(sent['script_args'], [])
        self.assertEqual(sent['timeout_seconds'], 120)
        self.assertIn('idempotency_key', sent)

    def test_action_run_creates_task_history_row(self):
        instance = self._make_instance('inst-rs-run-2')
        wizard = self._make_wizard(instance)
        task = _make_response({'task_id': 'task-rs-2'})
        status = _make_response({'state': 'running'})
        with patch(MOCK_PATH, side_effect=[task, status]):
            wizard.action_run()
        history = self.env['saas.task.history'].search(
            [('instance_id', '=', instance.id)],
        )
        self.assertEqual(len(history), 1)
        self.assertEqual(history.orchestrator_task_id, 'task-rs-2')
        self.assertEqual(history.operation_id, self.ops_by_code['restart'])

    @mute_logger('odoo.addons.saas_orchestrator.models.saas_instance')
    def test_action_run_raises_if_no_op_in_catalog(self):
        instance = self._make_instance('inst-rs-run-3', plan=self.plan_empty)
        wizard = self._make_wizard(instance)
        with self.assertRaises(UserError):
            wizard.action_run()


# =============================================================================
# Rotate password wizard
# =============================================================================
class TestSaasOperationRotatePasswordWizard(_Sprint3WizardBase):

    def test_has_rotate_password_operation_computed_true(self):
        instance = self._make_instance('inst-rp-1')
        self.assertTrue(instance.has_rotate_password_operation)

    def test_has_rotate_password_operation_computed_false(self):
        instance = self._make_instance('inst-rp-2', plan=self.plan_empty)
        self.assertFalse(instance.has_rotate_password_operation)

    def test_action_open_rotate_password_wizard_returns_action(self):
        instance = self._make_instance('inst-rp-3')
        result = instance.action_open_rotate_password_wizard()
        self.assertEqual(
            result.get('res_model'), 'saas.operation.rotate_password.wizard',
        )

    def test_action_open_rotate_password_raises_without_operation(self):
        instance = self._make_instance('inst-rp-4', plan=self.plan_empty)
        with self.assertRaises(UserError):
            instance.action_open_rotate_password_wizard()

    def _make_wizard(self, instance, notify_client=False, confirmed=True):
        return self.env['saas.operation.rotate_password.wizard'].create({
            'instance_id': instance.id,
            'notify_client': notify_client,
            'confirmed': confirmed,
        })

    @mute_logger('odoo.addons.saas_orchestrator.models.saas_instance')
    def test_action_run_requires_confirmation(self):
        instance = self._make_instance('inst-rp-run-1')
        wizard = self._make_wizard(instance, confirmed=False)
        with self.assertRaises(UserError):
            wizard.action_run()

    def test_action_run_builds_payload_with_notify_false(self):
        instance = self._make_instance('inst-rp-run-2')
        wizard = self._make_wizard(instance)
        task = _make_response({'task_id': 'task-rp-1'})
        status = _make_response({'state': 'running'})
        with patch(MOCK_PATH, side_effect=[task, status]) as mock_req:
            wizard.action_run()
        sent = mock_req.call_args_list[0][1]['json']
        self.assertEqual(sent['operation_code'], 'rotate_password')
        self.assertEqual(sent['script_args'], ['false'])

    def test_action_run_builds_payload_with_notify_true(self):
        instance = self._make_instance('inst-rp-run-3')
        wizard = self._make_wizard(instance, notify_client=True)
        task = _make_response({'task_id': 'task-rp-2'})
        status = _make_response({'state': 'running'})
        with patch(MOCK_PATH, side_effect=[task, status]) as mock_req:
            wizard.action_run()
        sent = mock_req.call_args_list[0][1]['json']
        self.assertEqual(sent['script_args'], ['true'])

    def test_action_run_creates_task_history_row(self):
        instance = self._make_instance('inst-rp-run-4')
        wizard = self._make_wizard(instance)
        task = _make_response({'task_id': 'task-rp-hist'})
        status = _make_response({'state': 'running'})
        with patch(MOCK_PATH, side_effect=[task, status]):
            wizard.action_run()
        history = self.env['saas.task.history'].search(
            [('instance_id', '=', instance.id)],
        )
        self.assertEqual(len(history), 1)
        self.assertEqual(history.orchestrator_task_id, 'task-rp-hist')


# =============================================================================
# Update env var wizard
# =============================================================================
class TestSaasOperationUpdateEnvVarWizard(_Sprint3WizardBase):

    def test_has_update_env_var_operation_computed_true(self):
        instance = self._make_instance('inst-ev-1')
        self.assertTrue(instance.has_update_env_var_operation)

    def test_has_update_env_var_operation_computed_false(self):
        instance = self._make_instance('inst-ev-2', plan=self.plan_empty)
        self.assertFalse(instance.has_update_env_var_operation)

    def test_action_open_update_env_var_wizard_returns_action(self):
        instance = self._make_instance('inst-ev-3')
        result = instance.action_open_update_env_var_wizard()
        self.assertEqual(
            result.get('res_model'), 'saas.operation.update_env_var.wizard',
        )

    def test_action_open_update_env_var_raises_without_operation(self):
        instance = self._make_instance('inst-ev-4', plan=self.plan_empty)
        with self.assertRaises(UserError):
            instance.action_open_update_env_var_wizard()

    def _make_wizard(self, instance, var_name='MY_VAR', var_value='hello',
                     is_secret=False):
        return self.env['saas.operation.update_env_var.wizard'].create({
            'instance_id': instance.id,
            'var_name': var_name,
            'var_value': var_value,
            'is_secret': is_secret,
        })

    def test_var_name_validator_rejects_lowercase(self):
        instance = self._make_instance('inst-ev-val-1')
        with self.assertRaises(ValidationError):
            self._make_wizard(instance, var_name='my_var')

    def test_var_name_validator_rejects_leading_digit(self):
        instance = self._make_instance('inst-ev-val-2')
        with self.assertRaises(ValidationError):
            self._make_wizard(instance, var_name='1FOO')

    def test_var_name_validator_rejects_dash(self):
        instance = self._make_instance('inst-ev-val-3')
        with self.assertRaises(ValidationError):
            self._make_wizard(instance, var_name='FOO-BAR')

    def test_var_name_validator_accepts_uppercase_underscore(self):
        instance = self._make_instance('inst-ev-val-4')
        wizard = self._make_wizard(instance, var_name='MY_VAR_2')
        self.assertEqual(wizard.var_name, 'MY_VAR_2')

    def test_action_run_builds_payload_3_args(self):
        instance = self._make_instance('inst-ev-run-1')
        wizard = self._make_wizard(instance, var_name='LOG_LEVEL', var_value='debug')
        task = _make_response({'task_id': 'task-ev-1'})
        status = _make_response({'state': 'running'})
        with patch(MOCK_PATH, side_effect=[task, status]) as mock_req:
            wizard.action_run()
        sent = mock_req.call_args_list[0][1]['json']
        self.assertEqual(sent['operation_code'], 'update_env_var')
        self.assertEqual(sent['script_args'], ['LOG_LEVEL', 'debug', 'false'])

    def test_action_run_with_secret_passes_true_flag(self):
        instance = self._make_instance('inst-ev-run-2')
        wizard = self._make_wizard(
            instance, var_name='API_KEY', var_value='sk-xxx', is_secret=True,
        )
        task = _make_response({'task_id': 'task-ev-2'})
        status = _make_response({'state': 'running'})
        with patch(MOCK_PATH, side_effect=[task, status]) as mock_req:
            wizard.action_run()
        sent = mock_req.call_args_list[0][1]['json']
        self.assertEqual(sent['script_args'], ['API_KEY', 'sk-xxx', 'true'])

    def test_action_run_creates_task_history_row(self):
        instance = self._make_instance('inst-ev-run-3')
        wizard = self._make_wizard(instance)
        task = _make_response({'task_id': 'task-ev-hist'})
        status = _make_response({'state': 'running'})
        with patch(MOCK_PATH, side_effect=[task, status]):
            wizard.action_run()
        history = self.env['saas.task.history'].search(
            [('instance_id', '=', instance.id)],
        )
        self.assertEqual(len(history), 1)
        self.assertEqual(history.orchestrator_task_id, 'task-ev-hist')

    @mute_logger('odoo.addons.saas_orchestrator.models.saas_instance')
    def test_action_run_http_error_propagates_as_user_error(self):
        instance = self._make_instance('inst-ev-run-4')
        wizard = self._make_wizard(instance)
        with patch(MOCK_PATH, side_effect=requests.exceptions.ConnectionError("Boom")):
            with self.assertRaises(UserError):
                wizard.action_run()
