from odoo import api, models

from .utils import build_instance_name, sanitize_slug


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _action_confirm(self):
        res = super()._action_confirm()
        self._create_saas_instances()
        return res

    def _create_saas_instances(self):
        """Create saas.instance for each SaaS product line in confirmed subscription orders."""
        for order in self:
            if not order.is_subscription:
                continue
            for line in order.order_line:
                product = line.product_id.product_tmpl_id
                if not product.saas_plan_id:
                    continue
                plan = product.saas_plan_id
                # Find or create tenant for this partner
                tenant = self.env['saas.tenant'].search([
                    ('partner_id', '=', order.partner_id.id),
                ], limit=1)
                if not tenant:
                    tenant = self.env['saas.tenant'].create({
                        'name': order.partner_id.name,
                        'partner_id': order.partner_id.id,
                        'slug': sanitize_slug(
                            f"{order.partner_id.name}-{order.partner_id.id}",
                            fallback=f"tenant-{order.partner_id.id}",
                        ),
                    })
                # Generate instance name (must match orchestrator API regex)
                instance_name = build_instance_name(
                    order.partner_id.name,
                    plan.blueprint_id.name,
                    order.id,
                )
                # Check if instance already exists for this subscription
                existing = self.env['saas.instance'].search([
                    ('subscription_id', '=', order.id),
                    ('plan_id', '=', plan.id),
                ], limit=1)
                if existing:
                    continue
                instance = self.env['saas.instance'].create({
                    'name': instance_name,
                    'tenant_id': tenant.id,
                    'plan_id': plan.id,
                    'subscription_id': order.id,
                    'state': 'draft',
                })
                instance.action_provision()
