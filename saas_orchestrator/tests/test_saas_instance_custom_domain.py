"""
Tests for the BYO custom domain feature: model fields, computed
effective_access_url, action methods, and the wizard 2-step flow.

The orchestrator HTTP layer is mocked at the same MOCK_PATH used by the
upgrade wizard tests, so the wizards never make a real network call.
"""

from unittest.mock import MagicMock, patch

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
class TestSaasInstanceCustomDomain(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param(
            'saas.orchestrator.url', 'http://test-api:8000',
        )
        cls.env['ir.config_parameter'].sudo().set_param(
            'saas.orchestrator.api_key', 'sk-test-key',
        )
        cls.partner = cls.env['res.partner'].create({'name': 'CD Partner'})
        cls.blueprint = cls.env['saas.product.blueprint'].create({
            'name': 'cd-bp',
            'domain': 'orquestio.com',
        })
        cls.plan = cls.env['saas.product.plan'].create({
            'name': 'cd-starter',
            'blueprint_id': cls.blueprint.id,
        })
        cls.tenant = cls.env['saas.tenant'].create({
            'name': 'cd-tenant',
            'partner_id': cls.partner.id,
        })

    def _make_instance(self, name='cd-inst-1', state='running'):
        return self.env['saas.instance'].create({
            'name': name,
            'tenant_id': self.tenant.id,
            'plan_id': self.plan.id,
            'state': state,
        })

    # ----- Computed effective_access_url -----

    def test_effective_url_no_custom_domain_uses_internal(self):
        instance = self._make_instance('eff-1')
        self.assertEqual(
            instance.effective_access_url,
            'https://eff-1.orquestio.com',
        )

    def test_effective_url_pending_custom_domain_uses_internal(self):
        instance = self._make_instance('eff-2')
        instance.write({
            'custom_domain': 'ai.acme.com',
            'custom_domain_status': 'pending',
        })
        self.assertEqual(
            instance.effective_access_url,
            'https://eff-2.orquestio.com',
        )

    def test_effective_url_active_custom_domain_uses_custom(self):
        instance = self._make_instance('eff-3')
        instance.write({
            'custom_domain': 'ai.acme.com',
            'custom_domain_status': 'active',
        })
        self.assertEqual(
            instance.effective_access_url,
            'https://ai.acme.com',
        )

    def test_effective_url_failed_custom_domain_uses_internal(self):
        instance = self._make_instance('eff-4')
        instance.write({
            'custom_domain': 'ai.acme.com',
            'custom_domain_status': 'failed',
        })
        self.assertEqual(
            instance.effective_access_url,
            'https://eff-4.orquestio.com',
        )

    # ----- Wizard input validation -----

    def test_wizard_rejects_invalid_domain(self):
        instance = self._make_instance('w-1')
        with self.assertRaises(ValidationError):
            self.env['saas.instance.custom_domain.wizard'].create({
                'instance_id': instance.id,
                'domain': 'no_underscore.com',
            })

    def test_wizard_rejects_single_label(self):
        instance = self._make_instance('w-2')
        with self.assertRaises(ValidationError):
            self.env['saas.instance.custom_domain.wizard'].create({
                'instance_id': instance.id,
                'domain': 'localhost',
            })

    def test_wizard_accepts_valid_domain(self):
        instance = self._make_instance('w-3')
        wizard = self.env['saas.instance.custom_domain.wizard'].create({
            'instance_id': instance.id,
            'domain': 'ai.acme.com',
        })
        self.assertEqual(wizard.domain, 'ai.acme.com')
        self.assertEqual(wizard.state, 'input')

    # ----- action_register full flow -----

    def test_register_calls_orchestrator_and_persists(self):
        instance = self._make_instance('w-reg-1')
        wizard = self.env['saas.instance.custom_domain.wizard'].create({
            'instance_id': instance.id,
            'domain': 'ai.acme.com',
        })
        # Plan B: orchestrator returns 202 with cname_target pointing at the
        # -direct unproxied A record, no cf_id, no cf_status.
        cf_resp = _make_response({
            'instance_id': instance.name,
            'domain': 'ai.acme.com',
            'status': 'pending',
            'cname_target': 'w-reg-1-direct.orquestio.com',
            'cf_id': None,
            'cf_status': None,
        }, status_code=202)
        status_resp = _make_response({'state': 'running'})
        with patch(MOCK_PATH, side_effect=[cf_resp, status_resp]) as mock_req:
            wizard.action_register()

        first = mock_req.call_args_list[0]
        self.assertEqual(first[0][0], 'POST')
        self.assertIn('/instances/w-reg-1/custom-domain', first[0][1])
        self.assertEqual(first[1]['json'], {'domain': 'ai.acme.com'})

        instance.invalidate_recordset()
        self.assertEqual(instance.custom_domain, 'ai.acme.com')
        self.assertEqual(instance.custom_domain_status, 'pending')
        self.assertEqual(wizard.state, 'instructions')
        self.assertEqual(wizard.cname_target, 'w-reg-1-direct.orquestio.com')

    @mute_logger('odoo.addons.saas_orchestrator.models.saas_instance')
    def test_register_409_translates_to_user_error(self):
        instance = self._make_instance('w-reg-2')
        wizard = self.env['saas.instance.custom_domain.wizard'].create({
            'instance_id': instance.id,
            'domain': 'ai.acme.com',
        })
        from requests.exceptions import HTTPError
        bad = _make_response({'detail': 'Domain in use'}, status_code=409)
        bad.raise_for_status = MagicMock(side_effect=HTTPError('409 Conflict', response=bad))
        with patch(MOCK_PATH, return_value=bad):
            with self.assertRaises(UserError):
                wizard.action_register()

    # ----- action_remove_custom_domain -----

    def test_remove_custom_domain_clears_local_state(self):
        instance = self._make_instance('w-rem-1')
        instance.write({
            'custom_domain': 'ai.acme.com',
            'custom_domain_status': 'active',
        })
        ok = _make_response({'instance_id': instance.name, 'custom_domain_removed': 'ai.acme.com'})
        status = _make_response({'state': 'running'})
        with patch(MOCK_PATH, side_effect=[ok, status]):
            instance.action_remove_custom_domain()
        self.assertFalse(instance.custom_domain)
        self.assertFalse(instance.custom_domain_status)

    def test_remove_custom_domain_raises_when_none(self):
        instance = self._make_instance('w-rem-2')
        with self.assertRaises(UserError):
            instance.action_remove_custom_domain()

    # ----- action_refresh_custom_domain -----

    def test_refresh_custom_domain_updates_status_to_active(self):
        instance = self._make_instance('w-ref-1')
        instance.write({
            'custom_domain': 'ai.acme.com',
            'custom_domain_status': 'pending',
        })
        cf_now_active = _make_response({
            'instance_id': instance.name,
            'domain': 'ai.acme.com',
            'status': 'active',
            'cname_target': 'w-ref-1-direct.orquestio.com',
            'cf_id': None,
            'cf_status': None,
        })
        with patch(MOCK_PATH, return_value=cf_now_active):
            instance.action_refresh_custom_domain()
        self.assertEqual(instance.custom_domain_status, 'active')

    def test_refresh_custom_domain_raises_when_none(self):
        instance = self._make_instance('w-ref-2')
        with self.assertRaises(UserError):
            instance.action_refresh_custom_domain()
