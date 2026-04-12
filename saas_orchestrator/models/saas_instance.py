import json
import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

API_TIMEOUT = 30


class SaasInstance(models.Model):
    _name = 'saas.instance'
    _description = 'SaaS Instance'
    _inherit = ['mail.thread']

    name = fields.Char(string='Instance ID', required=True, tracking=True)
    tenant_id = fields.Many2one('saas.tenant', required=True, tracking=True)
    plan_id = fields.Many2one('saas.product.plan', required=True, tracking=True)
    subscription_id = fields.Many2one('sale.order', string='Subscription')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('provisioning', 'Provisioning'),
        ('provisioning_failed', 'Provisioning Failed'),
        ('running', 'Running'),
        ('stopped', 'Stopped'),
        ('degraded', 'Degraded'),
        ('destroying', 'Destroying'),
        ('destroyed', 'Destroyed'),
    ], default='draft', required=True, tracking=True)
    ec2_instance_id = fields.Char()
    ip_address = fields.Char()
    access_url = fields.Char()
    access_password = fields.Char()
    dns_record_id = fields.Char()
    efs_id = fields.Char()
    secret_arn = fields.Char()
    terraform_state_path = fields.Char()
    cpu_usage = fields.Float(string='CPU %')
    ram_usage = fields.Float(string='RAM %')
    disk_usage = fields.Float(string='Disk %')
    last_health_check = fields.Datetime()
    last_state_fetch_at = fields.Datetime(
        string='Last State Refresh',
        help="Timestamp of the last successful refresh of instance state from the orchestrator.",
    )
    # Sprint 4: visibilidad de stale state. Computed selection drives the
    # decoration-* on the tree view so a sysadmin can spot at a glance
    # which instances haven't checked in recently:
    #   fresh   → ≤ 10 min
    #   stale   → 10 min – 1 h  (yellow)
    #   missing → > 1 h         (red)
    state_freshness = fields.Selection(
        [('fresh', 'Fresh'), ('stale', 'Stale'), ('missing', 'Missing')],
        compute='_compute_state_freshness',
        store=False,
        help="Color-coded freshness of last_state_fetch_at relative to now().",
    )
    env_var_ids = fields.One2many('saas.instance.env.var', 'instance_id')
    task_history_ids = fields.One2many(
        'saas.task.history', 'instance_id',
        string='Operation history',
        help="Control plane operations dispatched against this instance.",
    )
    current_version_id = fields.Many2one(
        'saas.openclaw.version', string='Current Version',
        help="The OpenClaw version currently running on this instance.",
    )
    active = fields.Boolean(default=True)

    @api.depends('last_state_fetch_at')
    def _compute_state_freshness(self):
        from datetime import timedelta
        now = fields.Datetime.now()
        for rec in self:
            if not rec.last_state_fetch_at:
                rec.state_freshness = 'missing'
                continue
            delta = now - rec.last_state_fetch_at
            if delta < timedelta(minutes=10):
                rec.state_freshness = 'fresh'
            elif delta < timedelta(hours=1):
                rec.state_freshness = 'stale'
            else:
                rec.state_freshness = 'missing'

    # BYO custom domain (Phase C). Customer optionally connects their own
    # hostname (e.g. ai.acme.com) via Cloudflare for SaaS. The internal
    # subdomain `<name>.orquestio.com` always exists; the custom domain
    # is layered on top.
    custom_domain = fields.Char(
        copy=False,
        tracking=True,
        help="Customer-owned hostname registered as a Cloudflare custom hostname.",
    )
    custom_domain_status = fields.Selection([
        ('pending', 'Pending DNS / cert'),
        ('active', 'Active'),
        ('failed', 'Failed'),
    ], copy=False, readonly=True, tracking=True)
    effective_access_url = fields.Char(
        compute='_compute_effective_access_url',
        help="HTTPS URL the customer should use: their custom domain if active, otherwise the internal subdomain.",
    )

    @api.depends('name', 'access_url', 'custom_domain', 'custom_domain_status')
    def _compute_effective_access_url(self):
        for rec in self:
            if rec.custom_domain and rec.custom_domain_status == 'active':
                rec.effective_access_url = f'https://{rec.custom_domain}'
            elif rec.access_url:
                rec.effective_access_url = rec.access_url
            else:
                rec.effective_access_url = f'https://{rec.name}.orquestio.com' if rec.name else False
    last_notification_sent = fields.Selection([
        ('suspension_warning', 'Suspension Warning'),
        ('suspended', 'Suspended'),
        ('destruction_warning', 'Destruction Warning'),
    ], help="Tracks last notification sent to avoid duplicates")

    # Computed flags that drive visibility of operation buttons in the form
    # view. Each flag reflects whether the instance's blueprint declares the
    # corresponding operation in its catalog (saas.product.operation).
    has_upgrade_operation = fields.Boolean(
        compute='_compute_available_operations',
        help="True if the instance blueprint declares the 'upgrade' operation in its catalog.",
    )
    has_restart_operation = fields.Boolean(
        compute='_compute_available_operations',
        help="True if the instance blueprint declares the 'restart' operation in its catalog.",
    )
    has_rotate_password_operation = fields.Boolean(
        compute='_compute_available_operations',
        help="True if the instance blueprint declares the 'rotate_password' operation in its catalog.",
    )
    has_update_env_var_operation = fields.Boolean(
        compute='_compute_available_operations',
        help="True if the instance blueprint declares the 'update_env_var' operation in its catalog.",
    )

    @api.depends('plan_id.blueprint_id.operation_ids.code')
    def _compute_available_operations(self):
        for rec in self:
            codes = set(rec.plan_id.blueprint_id.operation_ids.mapped('code'))
            rec.has_upgrade_operation = 'upgrade' in codes
            rec.has_restart_operation = 'restart' in codes
            rec.has_rotate_password_operation = 'rotate_password' in codes
            rec.has_update_env_var_operation = 'update_env_var' in codes

    # -------------------------------------------------------------------------
    # API helpers
    # -------------------------------------------------------------------------

    def _get_api_config(self):
        """Return (base_url, headers) from System Parameters."""
        ICP = self.env['ir.config_parameter'].sudo()
        base_url = ICP.get_param('saas.orchestrator.url', '').rstrip('/')
        api_key = ICP.get_param('saas.orchestrator.api_key', '')
        if not base_url or not api_key:
            raise UserError(_("Orchestrator API URL and API Key must be configured in System Parameters."))
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        return base_url, headers

    def _api_call(self, method, path, payload=None):
        """Execute an HTTP call to the orchestrator API and return the response dict."""
        base_url, headers = self._get_api_config()
        url = f"{base_url}{path}"
        try:
            response = requests.request(
                method, url, headers=headers,
                json=payload, timeout=API_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            raise UserError(_("Cannot connect to orchestrator API at %s", base_url))
        except requests.exceptions.Timeout:
            raise UserError(_("Orchestrator API timed out (%ss).", API_TIMEOUT))
        except requests.exceptions.HTTPError as e:
            body = ''
            try:
                body = e.response.text
            except Exception:
                pass
            raise UserError(_("Orchestrator API error %s: %s", e.response.status_code, body))

    # -------------------------------------------------------------------------
    # Actions — lifecycle
    # -------------------------------------------------------------------------

    def action_provision(self):
        """POST /instances/create — start provisioning."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Only draft instances can be provisioned."))
        blueprint = self.plan_id.blueprint_id
        payload = {
            'instance_id': self.name,
            'tenant_id': self.tenant_id.slug,
            'blueprint_name': blueprint.name,
            'plan_id': self.plan_id.name,
        }
        result = self._api_call('POST', '/instances/create', payload)
        self.write({
            'state': 'provisioning',
            'ec2_instance_id': result.get('ec2_id'),
            'ip_address': result.get('ip_address'),
            'access_url': result.get('access_url'),
        })
        self.message_post(body=_("Provisioning started."))

    def action_destroy(self):
        """DELETE /instances/{id} — destroy instance."""
        self.ensure_one()
        if self.state in ('destroyed', 'destroying'):
            raise UserError(_("Instance is already destroyed or being destroyed."))
        self._api_call('DELETE', f'/instances/{self.name}')
        self.write({'state': 'destroying'})
        self.message_post(body=_("Destruction started."))

    def action_stop(self):
        """POST /instances/{id}/stop"""
        self.ensure_one()
        if self.state != 'running':
            raise UserError(_("Only running instances can be stopped."))
        self._api_call('POST', f'/instances/{self.name}/stop')
        self.write({'state': 'stopped'})
        self.message_post(body=_("Instance stopped."))

    def action_start(self):
        """POST /instances/{id}/start"""
        self.ensure_one()
        if self.state != 'stopped':
            raise UserError(_("Only stopped instances can be started."))
        self._api_call('POST', f'/instances/{self.name}/start')
        self.write({'state': 'running'})
        self.message_post(body=_("Instance started."))

    def action_restart(self):
        """POST /instances/{id}/restart"""
        self.ensure_one()
        if self.state != 'running':
            raise UserError(_("Only running instances can be restarted."))
        self._api_call('POST', f'/instances/{self.name}/restart')
        self.message_post(body=_("Instance restarted."))

    # -------------------------------------------------------------------------
    # Refresh — on-demand state fetch from orchestrator
    # -------------------------------------------------------------------------

    def action_refresh(self):
        """Refresh instance state from orchestrator. Usable on one or many records."""
        if len(self) > 50:
            raise UserError(_(
                "Bulk refresh limited to 50 instances at a time (got %s). "
                "Select fewer and try again.", len(self),
            ))
        updated = 0
        failed = []
        for inst in self:
            try:
                data = inst._api_call('GET', f'/instances/{inst.name}/status')
                vals = {
                    'state': data.get('state', inst.state),
                    'ec2_instance_id': data.get('ec2_id') or inst.ec2_instance_id,
                    'ip_address': data.get('ip_address') or inst.ip_address,
                    'access_url': data.get('access_url') or inst.access_url,
                    'last_state_fetch_at': fields.Datetime.now(),
                }
                if data.get('cpu_usage') is not None:
                    vals['cpu_usage'] = data['cpu_usage']
                if data.get('ram_usage') is not None:
                    vals['ram_usage'] = data['ram_usage']
                if data.get('disk_usage') is not None:
                    vals['disk_usage'] = data['disk_usage']
                if data.get('last_health_check'):
                    vals['last_health_check'] = data['last_health_check'].replace('T', ' ')
                # Sync current_version from orchestrator
                cv = data.get('current_version')
                if cv:
                    version_rec = self.env['saas.openclaw.version'].sudo().search(
                        [('name', '=', cv)], limit=1,
                    )
                    if version_rec:
                        vals['current_version_id'] = version_rec.id
                inst.write(vals)
                updated += 1
            except Exception as e:
                _logger.warning("Failed to refresh instance %s: %s", inst.name, e)
                failed.append(inst.name)

        if len(self) == 1:
            # Single-record case: raise on failure, silent success (Odoo form auto-reloads)
            if failed:
                raise UserError(_("Failed to refresh instance: %s", failed[0]))
            return True

        # Bulk case: return a notification summarizing the batch
        if failed:
            msg = _("Refreshed %s instances. Failed: %s") % (updated, ', '.join(failed))
            msg_type = 'warning'
        else:
            msg = _("Refreshed %s instances.") % updated
            msg_type = 'success'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Refresh'),
                'message': msg,
                'type': msg_type,
                'sticky': False,
            },
        }

    # -------------------------------------------------------------------------
    # Operation wizards — dispatch declared operations from blueprint catalog
    # -------------------------------------------------------------------------

    def _dispatch_catalog_operation(
        self,
        op_code,
        script_args,
        idempotency_prefix,
        message,
        wizard_id=0,
    ):
        """Shared dispatch flow for the operation wizards.

        Looks up the operation in the blueprint catalog, posts to the
        orchestrator's `/instances/{name}/tasks` endpoint with the standard
        payload shape, creates a saas.task.history row, message_posts the
        success line, and best-effort refreshes the instance state.

        op_code:            operation_code in saas.product.operation
        script_args:        list[str] of positional args for the script
        idempotency_prefix: short label embedded in the idempotency_key
                            (e.g. 'restart', 'rotpwd', 'envvar')
        message:            chatter line to post on the instance after dispatch
        wizard_id:          id of the calling wizard (for idempotency_key
                            uniqueness across rapid clicks); pass 0 if N/A
        """
        self.ensure_one()
        operations = self.plan_id.blueprint_id.operation_ids.filtered(
            lambda o: o.code == op_code
        )
        if not operations:
            raise UserError(_(
                "The blueprint for this instance does not declare a %r operation."
            ) % op_code)
        op = operations.ensure_one()

        payload = {
            'operation_code': op.code,
            'script_path': op.script_path,
            'script_args': list(script_args),
            'timeout_seconds': op.timeout_seconds,
            'idempotency_key': (
                f'odoo-{idempotency_prefix}-{self.id}-{wizard_id}-'
                f'{fields.Datetime.now().isoformat()}'
            ),
        }

        try:
            response = self._api_call(
                'POST', f'/instances/{self.name}/tasks', payload,
            )
        except UserError as e:
            msg = str(e)
            if '409' in msg:
                raise UserError(_(
                    "Another operation is in progress on this instance. "
                    "Please wait for it to finish and retry."
                )) from e
            if '503' in msg:
                raise UserError(_(
                    "Control plane temporarily unavailable. "
                    "Please retry in a few seconds."
                )) from e
            raise

        self.env['saas.task.history'].create({
            'instance_id': self.id,
            'operation_id': op.id,
            'task_type': op.code,
            'orchestrator_task_id': response.get('task_id'),
            'state': 'in_progress',
            'payload': str(payload),
        })

        self.message_post(body=_(
            "%s (task %s).", message, response.get('task_id') or '-',
        ))

        # Refresh failures must not rollback the dispatch.
        try:
            self.action_refresh()
        except Exception:
            pass

        return response

    def action_open_upgrade_wizard(self):
        """Open the transient wizard to dispatch the 'upgrade' operation."""
        self.ensure_one()
        if not self.has_upgrade_operation:
            raise UserError(_(
                "This instance's blueprint does not declare an upgrade operation."
            ))
        return {
            'name': _('Upgrade %s', self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'saas.operation.upgrade.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_instance_id': self.id},
        }

    def action_open_restart_wizard(self):
        """Open the transient wizard to dispatch the 'restart' operation."""
        self.ensure_one()
        if not self.has_restart_operation:
            raise UserError(_(
                "This instance's blueprint does not declare a restart operation."
            ))
        return {
            'name': _('Restart %s', self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'saas.operation.restart.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_instance_id': self.id},
        }

    def action_open_rotate_password_wizard(self):
        """Open the transient wizard to dispatch the 'rotate_password' operation."""
        self.ensure_one()
        if not self.has_rotate_password_operation:
            raise UserError(_(
                "This instance's blueprint does not declare a rotate_password operation."
            ))
        return {
            'name': _('Rotate Password — %s', self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'saas.operation.rotate_password.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_instance_id': self.id},
        }

    def action_open_custom_domain_wizard(self):
        """Open the wizard to register or change a BYO custom domain."""
        self.ensure_one()
        return {
            'name': _('Custom Domain — %s', self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'saas.instance.custom_domain.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_instance_id': self.id,
                'default_domain': self.custom_domain or '',
            },
        }

    def action_remove_custom_domain(self):
        """Remove the registered custom domain via the orchestrator."""
        self.ensure_one()
        if not self.custom_domain:
            raise UserError(_("No custom domain to remove."))
        try:
            self._api_call('DELETE', f'/instances/{self.name}/custom-domain')
        except UserError as e:
            if '404' in str(e):
                # Already gone on the orchestrator side — just clear local state.
                pass
            else:
                raise
        old = self.custom_domain
        self.write({
            'custom_domain': False,
            'custom_domain_status': False,
        })
        self.message_post(body=_("Custom domain %s removed.", old))
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_refresh_custom_domain(self):
        """Pull the latest custom domain status from the orchestrator's local DB.

        Plan B: GET /custom-domain reads the orchestrator's row directly. The
        pending → active transition is driven by the post-success hook of
        the add_custom_domain control plane operation, not by this endpoint.
        """
        self.ensure_one()
        if not self.custom_domain:
            raise UserError(_("No custom domain to refresh."))
        response = self._api_call('GET', f'/instances/{self.name}/custom-domain')
        new_status = response.get('status')
        if new_status and new_status != self.custom_domain_status:
            self.custom_domain_status = new_status
            self.message_post(body=_(
                "Custom domain %s status changed to %s.",
                self.custom_domain, new_status,
            ))
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_open_update_env_var_wizard(self):
        """Open the transient wizard to dispatch the 'update_env_var' operation."""
        self.ensure_one()
        if not self.has_update_env_var_operation:
            raise UserError(_(
                "This instance's blueprint does not declare an update_env_var operation."
            ))
        return {
            'name': _('Update Env Var — %s', self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'saas.operation.update_env_var.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_instance_id': self.id},
        }

    def _cron_purge_task_history(self):
        """Purge task history exceeding plan limits."""
        instances = self.search([('state', '!=', 'destroyed')])
        TaskHistory = self.env['saas.task.history']
        for inst in instances:
            plan = inst.plan_id
            domain = [('instance_id', '=', inst.id)]
            # Purge by retention days
            if plan.history_retention_days > 0:
                cutoff = fields.Datetime.subtract(fields.Datetime.now(), days=plan.history_retention_days)
                old = TaskHistory.search(domain + [('created_at', '<', cutoff)])
                if old:
                    old.unlink()
            # Purge by max records
            if plan.history_max_records > 0:
                count = TaskHistory.search_count(domain)
                if count > plan.history_max_records:
                    excess = TaskHistory.search(domain, order='created_at asc', limit=count - plan.history_max_records)
                    excess.unlink()

    # -------------------------------------------------------------------------
    # Cron — subscription status check (non-payment / cancellation)
    # -------------------------------------------------------------------------

    def _cron_check_subscription_status(self):
        """Check subscription status and suspend/destroy/reactivate instances."""
        now = fields.Date.today()
        instances = self.search([
            ('state', 'in', ('running', 'stopped')),
            ('subscription_id', '!=', False),
        ])
        for inst in instances:
            try:
                sub = inst.subscription_id
                sub_state = sub.subscription_state
                expiry_date = sub.next_invoice_date

                # Reactivate stopped instances when subscription becomes active
                if sub_state == '3_progress' and inst.state == 'stopped':
                    inst.action_start()
                    inst.last_notification_sent = False
                    inst.message_post(
                        body=_("Instance reactivated — payment received."),
                    )
                    continue

                # Handle churned / cancelled subscriptions
                if sub_state in ('6_churn',) and inst.state == 'running':
                    if not expiry_date:
                        continue
                    days_expired = (now - expiry_date).days
                    if days_expired > 30:
                        inst.action_stop()
                        inst.message_post(
                            body=_("Instance suspended due to non-payment."),
                        )
                        if inst.last_notification_sent != 'suspended':
                            template = self.env.ref('saas_orchestrator.mail_template_instance_suspended')
                            template.send_mail(inst.id, force_send=False)
                            inst.last_notification_sent = 'suspended'
                        inst.action_destroy()
                        inst.message_post(
                            body=_("Instance destroyed after 30 days of non-payment."),
                        )
                    elif days_expired >= 7:
                        inst.action_stop()
                        inst.message_post(
                            body=_("Instance suspended due to non-payment."),
                        )
                        if inst.last_notification_sent != 'suspended':
                            template = self.env.ref('saas_orchestrator.mail_template_instance_suspended')
                            template.send_mail(inst.id, force_send=False)
                            inst.last_notification_sent = 'suspended'
                    elif days_expired >= 1:
                        if inst.last_notification_sent != 'suspension_warning':
                            template = self.env.ref('saas_orchestrator.mail_template_instance_suspension_warning')
                            template.send_mail(inst.id, force_send=False)
                            inst.last_notification_sent = 'suspension_warning'

                # Handle stopped instances past 30 days — destroy
                if sub_state in ('6_churn',) and inst.state == 'stopped':
                    if not expiry_date:
                        continue
                    days_expired = (now - expiry_date).days
                    if days_expired > 30:
                        inst.action_destroy()
                        inst.message_post(
                            body=_("Instance destroyed after 30 days of non-payment."),
                        )
                    elif days_expired >= 23:
                        if inst.last_notification_sent != 'destruction_warning':
                            template = self.env.ref('saas_orchestrator.mail_template_instance_destruction_warning')
                            template.send_mail(inst.id, force_send=False)
                            inst.last_notification_sent = 'destruction_warning'

            except Exception as e:
                _logger.warning(
                    "Failed to check subscription status for instance %s: %s",
                    inst.name, e,
                )
