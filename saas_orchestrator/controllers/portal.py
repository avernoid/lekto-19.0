"""
Sprint 5 — Customer portal controllers for SaaS instances.

Routes
------
GET  /my/instances                              → list page
GET  /my/instances/<int:instance_id>            → detail page
POST /my/instances/<int:instance_id>/refresh    → call action_refresh
POST /my/instances/<int:instance_id>/operations/<string:op_code>/run
                                                → dispatch a catalog op via the
                                                  internal _dispatch_catalog_operation helper
POST /my/instances/<int:instance_id>/custom-domain/add
                                                → register a BYO custom domain
POST /my/instances/<int:instance_id>/custom-domain/remove
                                                → unregister the BYO custom domain

The portal user is filtered by ir.rule (saas_instance_portal_rule) so any
attempt to address an instance not owned by the user's partner returns a 404.
We never read tenant_id.partner_id directly here — the rule does it.
"""
import logging

from odoo import http, _
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

_logger = logging.getLogger(__name__)


class SaasInstancePortal(CustomerPortal):

    # ---- Portal home counters --------------------------------------------

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'saas_instances_count' in counters:
            values['saas_instances_count'] = (
                request.env['saas.instance'].search_count([])
                if request.env['saas.instance'].has_access('read')
                else 0
            )
        return values

    # ---- Helpers ---------------------------------------------------------

    def _get_instance_or_404(self, instance_id):
        try:
            instance = request.env['saas.instance'].browse(int(instance_id))
            instance.check_access('read')
            instance.read(['name'])  # forces ir.rule check
        except (AccessError, MissingError):
            return None
        return instance if instance.exists() else None

    # ---- List page -------------------------------------------------------

    @http.route(['/my/instances', '/my/instances/page/<int:page>'],
                type='http', auth='user', website=True)
    def portal_my_instances(self, page=1, **kw):
        Instance = request.env['saas.instance']
        domain = []
        instance_count = Instance.search_count(domain)
        pager = portal_pager(
            url='/my/instances',
            total=instance_count,
            page=page,
            step=20,
        )
        instances = Instance.search(
            domain,
            order='create_date desc',
            limit=20,
            offset=pager['offset'],
        )
        values = {
            'instances': instances,
            'page_name': 'instances',
            'pager': pager,
            'default_url': '/my/instances',
        }
        return request.render('saas_orchestrator.portal_my_instances', values)

    # ---- Detail page -----------------------------------------------------

    @http.route(['/my/instances/<int:instance_id>'],
                type='http', auth='user', website=True)
    def portal_my_instance_detail(self, instance_id, **kw):
        instance = self._get_instance_or_404(instance_id)
        if not instance:
            return request.redirect('/my')
        values = {
            'instance': instance,
            'page_name': 'instance_detail',
        }
        return request.render('saas_orchestrator.portal_my_instance_detail', values)

    # ---- Refresh action --------------------------------------------------

    @http.route(['/my/instances/<int:instance_id>/refresh'],
                type='http', auth='user', methods=['POST'], website=True,
                csrf=True)
    def portal_my_instance_refresh(self, instance_id, **kw):
        instance = self._get_instance_or_404(instance_id)
        if not instance:
            return request.redirect('/my')
        try:
            instance.sudo().action_refresh()
        except Exception as e:  # noqa: BLE001
            _logger.warning("Portal refresh failed for instance %s: %s", instance_id, e)
        return request.redirect(f'/my/instances/{instance_id}')

    # ---- Catalog operation dispatch (Sprint 1.4 dispatcher) --------------

    @http.route(['/my/instances/<int:instance_id>/operations/<string:op_code>/run'],
                type='http', auth='user', methods=['POST'], website=True,
                csrf=True)
    def portal_my_instance_run_operation(self, instance_id, op_code, **kw):
        instance = self._get_instance_or_404(instance_id)
        if not instance:
            return request.redirect('/my')

        # Find the operation in the blueprint catalog (must be portal-visible)
        operation = (
            instance.plan_id.blueprint_id.operation_ids
            .filtered(lambda o: o.code == op_code and o.visible_in_portal)
            [:1]
        )
        if not operation:
            _logger.warning(
                "Portal user attempted to run unknown/hidden operation %r on instance %s",
                op_code, instance_id,
            )
            return request.redirect(f'/my/instances/{instance_id}')

        # Build script_args from the form payload following operation.param_ids order
        script_args = []
        for param in operation.param_ids:
            raw = kw.get(param.name)
            if param.type == 'boolean':
                value = 'true' if raw in ('on', 'true', '1', 'yes') else 'false'
            else:
                value = (raw or '').strip()
                if param.required and not value:
                    _logger.info(
                        "Portal op %s missing required param %s — aborting", op_code, param.name,
                    )
                    return request.redirect(f'/my/instances/{instance_id}')
            script_args.append(value)

        try:
            instance.sudo()._dispatch_catalog_operation(
                op_code=op_code,
                script_args=script_args,
                idempotency_prefix=f'portal-{op_code}',
                message=_("Operation %s dispatched from customer portal.") % op_code,
                wizard_id=0,
            )
        except UserError as e:
            _logger.info("Portal op %s on %s rejected: %s", op_code, instance_id, e)
        except Exception as e:  # noqa: BLE001
            _logger.exception("Portal op %s on %s crashed: %s", op_code, instance_id, e)
        return request.redirect(f'/my/instances/{instance_id}')

    # ---- Custom domain ---------------------------------------------------

    @http.route(['/my/instances/<int:instance_id>/custom-domain/add'],
                type='http', auth='user', methods=['POST'], website=True,
                csrf=True)
    def portal_my_instance_add_custom_domain(self, instance_id, domain=None, **kw):
        instance = self._get_instance_or_404(instance_id)
        if not instance:
            return request.redirect('/my')
        if not domain:
            return request.redirect(f'/my/instances/{instance_id}')
        try:
            wizard = request.env['saas.instance.custom_domain.wizard'].sudo().create({
                'instance_id': instance.id,
                'domain': domain.strip().lower(),
            })
            wizard.action_register()
        except (UserError, ValidationError) as e:
            _logger.info("Portal custom-domain add on %s failed: %s", instance_id, e)
        except Exception as e:  # noqa: BLE001
            _logger.exception("Portal custom-domain add on %s crashed: %s", instance_id, e)
        return request.redirect(f'/my/instances/{instance_id}')

    @http.route(['/my/instances/<int:instance_id>/custom-domain/remove'],
                type='http', auth='user', methods=['POST'], website=True,
                csrf=True)
    def portal_my_instance_remove_custom_domain(self, instance_id, **kw):
        instance = self._get_instance_or_404(instance_id)
        if not instance:
            return request.redirect('/my')
        try:
            instance.sudo().action_remove_custom_domain()
        except UserError as e:
            _logger.info("Portal custom-domain remove on %s rejected: %s", instance_id, e)
        except Exception as e:  # noqa: BLE001
            _logger.exception("Portal custom-domain remove on %s crashed: %s", instance_id, e)
        return request.redirect(f'/my/instances/{instance_id}')
