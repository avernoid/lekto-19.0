import json
import logging

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

_logger = logging.getLogger(__name__)


class SaasPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'instance_count' in counters:
            partner = request.env.user.partner_id
            values['instance_count'] = request.env['saas.instance'].sudo().search_count([
                ('tenant_id.partner_id', '=', partner.id),
                ('state', '!=', 'destroyed'),
            ])
        return values

    def _get_instance_or_redirect(self, instance_id):
        """Return instance if owned by current user, else None."""
        partner = request.env.user.partner_id
        instance = request.env['saas.instance'].sudo().browse(instance_id)
        if not instance.exists() or instance.tenant_id.partner_id != partner:
            return None
        return instance

    @http.route('/my/instances', type='http', auth='user', website=True)
    def portal_my_instances(self, **kwargs):
        partner = request.env.user.partner_id
        instances = request.env['saas.instance'].sudo().search([
            ('tenant_id.partner_id', '=', partner.id),
            ('state', '!=', 'destroyed'),
        ])
        return request.render('saas_portal.portal_my_instances', {
            'instances': instances,
            'page_name': 'instances',
        })

    @http.route('/my/instances/<int:instance_id>', type='http', auth='user', website=True)
    def portal_instance_detail(self, instance_id, **kwargs):
        instance = self._get_instance_or_redirect(instance_id)
        if not instance:
            return request.redirect('/my/instances')
        # Fetch version info from orchestrator if instance has a version
        version_info = None
        if instance.current_version_id:
            try:
                version_info = instance.sudo()._api_call(
                    'GET', f'/instances/{instance.name}/version-info',
                )
            except Exception as e:
                _logger.warning("Failed to fetch version info for %s: %s", instance.name, e)
        return request.render('saas_portal.portal_instance_detail', {
            'instance': instance,
            'version_info': version_info,
            'page_name': 'instance_detail',
        })

    @http.route('/my/instances/<int:instance_id>/restart', type='http', auth='user',
                website=True, methods=['POST'])
    def portal_instance_restart(self, instance_id, **kwargs):
        instance = self._get_instance_or_redirect(instance_id)
        if not instance:
            return request.redirect('/my/instances')
        try:
            instance.sudo().action_restart()
            return request.redirect(f'/my/instances/{instance_id}?message=Instance restarted successfully.')
        except Exception as e:
            _logger.warning("Portal restart failed for instance %s: %s", instance_id, e)
            return request.redirect(f'/my/instances/{instance_id}?error=Restart failed: {e}')

    @http.route('/my/instances/<int:instance_id>/upgrade', type='http', auth='user',
                website=True, methods=['POST'])
    def portal_instance_upgrade(self, instance_id, **kwargs):
        instance = self._get_instance_or_redirect(instance_id)
        if not instance:
            return request.redirect('/my/instances')
        target_version = kwargs.get('target_version', '').strip()
        if not target_version:
            return request.redirect(f'/my/instances/{instance_id}?error=No target version specified.')
        if instance.state != 'running':
            return request.redirect(f'/my/instances/{instance_id}?error=Instance must be running to upgrade.')
        try:
            instance.sudo()._dispatch_catalog_operation('upgrade', {'target_version': target_version})
            return request.redirect(
                f'/my/instances/{instance_id}?message=Upgrade to {target_version} initiated. '
                f'The instance will be briefly unavailable (~1 minute).'
            )
        except Exception as e:
            _logger.warning("Portal upgrade failed for instance %s: %s", instance_id, e)
            return request.redirect(f'/my/instances/{instance_id}?error=Upgrade failed: {e}')

    @http.route('/my/instances/<int:instance_id>/credentials', type='http', auth='user',
                methods=['POST'], csrf=True)
    def portal_instance_credentials(self, instance_id, **kwargs):
        instance = self._get_instance_or_redirect(instance_id)
        if not instance:
            return request.make_json_response({'error': 'Not found'}, status=404)
        return request.make_json_response({
            'access_password': instance.access_password or '',
        })

    @http.route('/my/instances/<int:instance_id>/env-vars', type='http', auth='user',
                website=True, methods=['POST'])
    def portal_instance_add_env_var(self, instance_id, **kwargs):
        instance = self._get_instance_or_redirect(instance_id)
        if not instance:
            return request.redirect('/my/instances')
        name = kwargs.get('name', '').strip()
        value = kwargs.get('value', '').strip()
        if not name or not value:
            return request.redirect(f'/my/instances/{instance_id}?error=Name and value are required.')
        # Check env var limit
        plan = instance.plan_id
        env_var_limit = plan.env_vars_included
        current_count = len(instance.env_var_ids)
        if env_var_limit > 0 and current_count >= env_var_limit:
            return request.redirect(
                f'/my/instances/{instance_id}?error=Environment variable limit reached ({env_var_limit}).'
            )
        try:
            request.env['saas.instance.env.var'].sudo().create({
                'instance_id': instance.id,
                'name': name,
                'value': value,
            })
            return request.redirect(f'/my/instances/{instance_id}?message=Variable added.')
        except Exception as e:
            _logger.warning("Portal add env var failed for instance %s: %s", instance_id, e)
            return request.redirect(f'/my/instances/{instance_id}?error=Failed to add variable.')

    @http.route('/my/instances/<int:instance_id>/env-vars/<int:var_id>/delete', type='http',
                auth='user', website=True, methods=['POST'])
    def portal_instance_delete_env_var(self, instance_id, var_id, **kwargs):
        instance = self._get_instance_or_redirect(instance_id)
        if not instance:
            return request.redirect('/my/instances')
        env_var = request.env['saas.instance.env.var'].sudo().browse(var_id)
        if not env_var.exists() or env_var.instance_id.id != instance.id:
            return request.redirect(f'/my/instances/{instance_id}?error=Variable not found.')
        try:
            env_var.unlink()
            return request.redirect(f'/my/instances/{instance_id}?message=Variable deleted.')
        except Exception as e:
            _logger.warning("Portal delete env var failed for instance %s: %s", instance_id, e)
            return request.redirect(f'/my/instances/{instance_id}?error=Failed to delete variable.')
