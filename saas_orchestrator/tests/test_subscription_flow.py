from datetime import timedelta
from unittest.mock import MagicMock, patch

from odoo import fields
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
class TestSubscriptionFlow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('saas.orchestrator.url', 'http://test-api:8000')
        cls.env['ir.config_parameter'].sudo().set_param('saas.orchestrator.api_key', 'sk-test-key')

        cls.partner = cls.env['res.partner'].create({'name': 'Test Subscription Partner'})
        cls.blueprint = cls.env['saas.product.blueprint'].create({
            'name': 'openclaw',
            'domain': 'orquestio.com',
        })
        cls.plan = cls.env['saas.product.plan'].create({
            'name': 'starter',
            'blueprint_id': cls.blueprint.id,
        })
        cls.tenant = cls.env['saas.tenant'].create({
            'name': 'tenant-sub-001',
            'partner_id': cls.partner.id,
        })

        cls.subscription = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
        })

        cls.instance = cls.env['saas.instance'].create({
            'name': 'inst-sub-001',
            'tenant_id': cls.tenant.id,
            'plan_id': cls.plan.id,
            'state': 'running',
            'subscription_id': cls.subscription.id,
        })

    def test_suspend_after_7_days(self):
        self.instance.write({'state': 'running'})
        self.subscription.write({
            'subscription_state': '6_churn',
            'next_invoice_date': fields.Date.today() - timedelta(days=10),
        })
        with patch(MOCK_PATH, return_value=_make_response({})):
            self.env['saas.instance']._cron_check_subscription_status()
        self.assertEqual(self.instance.state, 'stopped')

    def test_destroy_after_30_days_from_running(self):
        self.instance.write({'state': 'running'})
        self.subscription.write({
            'subscription_state': '6_churn',
            'next_invoice_date': fields.Date.today() - timedelta(days=35),
        })
        with patch(MOCK_PATH, return_value=_make_response({})):
            self.env['saas.instance']._cron_check_subscription_status()
        self.assertEqual(self.instance.state, 'destroying')

    def test_destroy_after_30_days_from_stopped(self):
        self.instance.write({'state': 'stopped'})
        self.subscription.write({
            'subscription_state': '6_churn',
            'next_invoice_date': fields.Date.today() - timedelta(days=35),
        })
        with patch(MOCK_PATH, return_value=_make_response({})):
            self.env['saas.instance']._cron_check_subscription_status()
        self.assertEqual(self.instance.state, 'destroying')

    def test_no_action_before_7_days(self):
        self.instance.write({'state': 'running'})
        self.subscription.write({
            'subscription_state': '6_churn',
            'next_invoice_date': fields.Date.today() - timedelta(days=3),
        })
        with patch(MOCK_PATH, return_value=_make_response({})):
            self.env['saas.instance']._cron_check_subscription_status()
        self.assertEqual(self.instance.state, 'running')

    def test_reactivate_on_payment(self):
        self.instance.write({'state': 'stopped'})
        self.subscription.write({
            'subscription_state': '3_progress',
        })
        with patch(MOCK_PATH, return_value=_make_response({})):
            self.env['saas.instance']._cron_check_subscription_status()
        self.assertEqual(self.instance.state, 'running')

    def test_skip_instance_without_subscription(self):
        instance_no_sub = self.env['saas.instance'].create({
            'name': 'inst-no-sub',
            'tenant_id': self.tenant.id,
            'plan_id': self.plan.id,
            'state': 'running',
        })
        with patch(MOCK_PATH, return_value=_make_response({})):
            self.env['saas.instance']._cron_check_subscription_status()
        self.assertEqual(instance_no_sub.state, 'running')

    @mute_logger('odoo.addons.saas_orchestrator.models.saas_instance')
    def test_cron_continues_on_individual_failure(self):
        self.instance.write({'state': 'stopped'})
        self.subscription.write({
            'subscription_state': '3_progress',
        })

        instance2_sub = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        instance2_sub.write({
            'subscription_state': '3_progress',
        })
        instance2 = self.env['saas.instance'].create({
            'name': 'inst-sub-002',
            'tenant_id': self.tenant.id,
            'plan_id': self.plan.id,
            'state': 'stopped',
            'subscription_id': instance2_sub.id,
        })

        # First call raises, second succeeds
        with patch(MOCK_PATH, side_effect=[
            Exception("API down"),
            _make_response({}),
        ]):
            self.env['saas.instance']._cron_check_subscription_status()

        # At least one should have been processed successfully
        # We can't guarantee order, but at least one should be 'running'
        states = [self.instance.state, instance2.state]
        self.assertIn('running', states, "At least one instance should have been reactivated")
