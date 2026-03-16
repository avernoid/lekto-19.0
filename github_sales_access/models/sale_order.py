import logging

from odoo import _, api, fields, models

from .github_sales_access import _ACTIVE_SUBSCRIPTION_STATES

_CLOSED_SUBSCRIPTION_STATES = ('4_paused', '6_churn')

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    github_access_ids = fields.One2many(
        comodel_name='github.sales.access',
        inverse_name='order_id',
        string='Accesos GitHub',
    )
    github_access_count = fields.Integer(
        string='Nº Accesos GitHub',
        compute='_compute_github_access_count',
    )
    has_github_connector_lines = fields.Boolean(
        string='Tiene líneas GitHub Connector',
        compute='_compute_has_github_connector_lines',
        store=True,
    )

    @api.depends('github_access_ids')
    def _compute_github_access_count(self):
        for order in self:
            order.github_access_count = len(order.github_access_ids)

    @api.depends('order_line.product_id.product_tmpl_id.github_product_type')
    def _compute_has_github_connector_lines(self):
        for order in self:
            order.has_github_connector_lines = any(
                line.product_id.product_tmpl_id.github_product_type == 'connector'
                for line in order.order_line
            )

    def action_view_github_accesses(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'github_sales_access.action_github_sales_access_all'
        )
        action['domain'] = [('order_id', '=', self.id)]
        action['context'] = {'default_order_id': self.id}
        gh_lines = self.order_line.filtered(
            lambda l: l.product_id.product_tmpl_id.github_product_type == 'connector'
        )
        if len(gh_lines) == 1:
            action['context']['default_order_line_id'] = gh_lines.id
        return action

    def action_generate_github_accesses(self):
        """Genera manualmente los registros github.sales.access para pedidos
        ya confirmados (regularización de datos históricos).

        Útil cuando el módulo se instala con pedidos existentes que nunca
        pasaron por action_confirm con la lógica de auto-creación activa.
        Puede llamarse desde el botón del formulario o como server action
        en lote desde la vista lista de pedidos.
        """
        created_total = 0
        for order in self.filtered(lambda o: o.subscription_state in _ACTIVE_SUBSCRIPTION_STATES):
            before = len(order.github_access_ids)
            order._create_github_access_records()
            created_total += len(order.github_access_ids) - before

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Accesos GitHub generados'),
                'message': _('%d registro(s) de acceso creados.') % created_total,
                'type': 'success' if created_total else 'warning',
                'sticky': False,
            },
        }

    # ── Auto-creation on confirm ─────────────────────────────────────────────

    def action_confirm(self):
        res = super().action_confirm()
        # La creación de accesos GitHub ya NO ocurre en action_confirm.
        # Se dispara cuando subscription_state transiciona a '3_progress'
        # (ver write() más abajo). Esto cubre tanto la primera activación
        # como re-activaciones desde 4_paused / 6_churn.
        return res

    def _revoke_github_access_for_order(self, order, state_label):
        """Revoca todos los repos activos o pending de los accesos connector
        vinculados a esta orden.

        Llama a action_auto_revoke() en cada repo hijo elegible.
        Nunca lanza excepción — el flujo de suscripción no se interrumpe.

        :param order: sale.order — la orden a procesar
        :param state_label: str — etiqueta del nuevo estado (para el chatter)
        """
        connector_accesses = order.github_access_ids.filtered(
            lambda a: a.order_line_id
            and a.order_line_id.product_id.product_tmpl_id.github_product_type == 'connector'
        )
        if not connector_accesses:
            return

        _logger.info(
            'GITHUB ACCESS AUTO-REVOKE: Processing %d access(es) for order %s (%s).',
            len(connector_accesses), order.name, state_label,
        )

        for access in connector_accesses:
            repos_to_revoke = access.repo_ids.filtered(
                lambda r: r.github_status not in ('revoke', 'inactive', 'error')
            )
            if repos_to_revoke:
                repos_to_revoke.action_auto_revoke(reason=state_label)

    def _get_maintained_repos_for_partner(self, partner, current_order=None):
        """Returns the github.repository records currently covered by an active
        maintenance fee subscription for the given partner.

        A maintenance fee is considered active when its order's subscription_state
        is in _ACTIVE_SUBSCRIPTION_STATES. The current_order (being confirmed) is
        always included, so buying the fee and the connector in the same order works.

        :param partner: res.partner — the order partner (partner_id, not commercial)
        :param current_order: sale.order — the order being confirmed (optional)
        :return: recordset of github.repository without duplicates
        """
        _ACTIVE = _ACTIVE_SUBSCRIPTION_STATES
        # Search existing active subscriptions for this partner
        domain = [
            ('order_id.partner_id', '=', partner.id),
            ('order_id.state', '=', 'sale'),
            ('order_id.subscription_state', 'in', _ACTIVE),
            ('product_id.product_tmpl_id.github_product_type', '=', 'maintenance_fee'),
        ]
        lines = self.env['sale.order.line'].search(domain)

        # Always include lines from the current order being confirmed,
        # even if its state/subscription_state is not yet propagated
        if current_order:
            current_fee_lines = current_order.order_line.filtered(
                lambda l: l.product_id.product_tmpl_id.github_product_type == 'maintenance_fee'
            )
            lines |= current_fee_lines

        repos = lines.mapped('product_id.product_tmpl_id.github_repository_ids')
        _logger.info(
            'GITHUB ACCESS: Maintenance fee filter for partner "%s": %d repo(s) covered.',
            partner.display_name, len(repos),
        )
        return repos

    def _create_github_access_records(self):
        """Crea registros github.sales.access al confirmar el pedido.

        Por cada línea conector crea N registros padre (N = int(product_uom_qty)),
        uno por usuario a asignar. Si ya existen registros previos para la línea
        (re-ejecución / regularización), solo crea los que falten hasta alcanzar
        la cantidad actual.
        """
        self.ensure_one()
        Access = self.env['github.sales.access']
        RepoLine = self.env['github.sales.access.repo']

        connector_lines = self.order_line.filtered(
            lambda l: l.product_id.product_tmpl_id.github_product_type == 'connector'
        )
        if not connector_lines:
            return

        # Repos covered by an active maintenance fee for this partner
        # (computed once per order, shared across all connector lines)
        maintained_repos = self._get_maintained_repos_for_partner(
            partner=self.partner_id,
            current_order=self,
        )

        for line in connector_lines:
            tmpl = line.product_id.product_tmpl_id
            # Step 1: candidate repos (based on repos_default_mode)
            candidate_repos = tmpl.get_github_repos_for_partner(
                partner=self.partner_id,
                current_order=self,
            )
            # Step 2: filter by maintenance fee (condition 2 of 3)
            if maintained_repos:
                repos = candidate_repos & maintained_repos
                excluded = candidate_repos - maintained_repos
                if excluded:
                    _logger.info(
                        'GITHUB ACCESS: Excluded %d repo(s) for line %d (order %s) '
                        'because no active maintenance fee covers them: %s',
                        len(excluded), line.id, self.name,
                        ', '.join(excluded.mapped('complete_name')),
                    )
            else:
                # No maintenance fee at all — exclude all candidate repos
                repos = self.env['github.repository']
                if candidate_repos:
                    _logger.info(
                        'GITHUB ACCESS: All %d candidate repo(s) excluded for line %d '
                        '(order %s) — no active maintenance fee found for partner "%s".',
                        len(candidate_repos), line.id, self.name,
                        self.partner_id.display_name,
                    )

            if not repos:
                _logger.info(
                    'GITHUB ACCESS: No repos qualify for line %d (order %s). '
                    'Access records will be created without repo lines.',
                    line.id, self.name,
                )

            # Cantidad de usuarios contratados en esta línea
            qty_needed = int(line.product_uom_qty)

            # Accesos ya existentes para esta línea
            existing = Access.search([('order_line_id', '=', line.id)])
            existing_count = len(existing)

            # Añadir repos que falten a los accesos ya existentes
            for parent in existing:
                for repo in repos:
                    already = RepoLine.search([
                        ('access_id', '=', parent.id),
                        ('repository_id', '=', repo.id),
                    ], limit=1)
                    if not already:
                        RepoLine.create({
                            'access_id': parent.id,
                            'repository_id': repo.id,
                            'github_status': 'pending',
                        })

            # Crear accesos padres que falten hasta llegar a qty_needed
            to_create = qty_needed - existing_count
            if to_create <= 0:
                continue

            _logger.info(
                'GITHUB ACCESS: Creating %d access record(s) for line %d '
                '(order %s, qty=%d, existing=%d).',
                to_create, line.id, self.name, qty_needed, existing_count,
            )

            for _i in range(to_create):
                parent = Access.create({'order_line_id': line.id})
                for repo in repos:
                    RepoLine.create({
                        'access_id': parent.id,
                        'repository_id': repo.id,
                        'github_status': 'pending',
                    })

            _logger.info(
                'GITHUB ACCESS: Access records created for line %d '
                '(partner "%s", order %s, repos_per_access=%d).',
                line.id, self.partner_id.display_name, self.name, len(repos),
            )

    # ── Semi-automatic on cancel ─────────────────────────────────────────────

    def action_cancel(self):
        res = super().action_cancel()
        for order in self:
            # Accesos padre con al menos un repo hijo activo
            accesses_with_active_repos = order.github_access_ids.filtered(
                lambda a: any(r.github_status == 'active' for r in a.repo_ids)
            )
            for access in accesses_with_active_repos:
                active_repos = access.repo_ids.filtered(
                    lambda r: r.github_status == 'active'
                )
                active_repos.write({'github_status': 'pending'})
                repo_names = ', '.join(active_repos.mapped('repository_id.complete_name'))
                access.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_('Pedido cancelado — revisar accesos GitHub'),
                    note=_(
                        'El pedido <b>%(order)s</b> ha sido cancelado.<br/>'
                        'El usuario <b>%(user)s</b> tiene accesos activos en:<br/>'
                        '<b>%(repos)s</b><br/><br/>'
                        'Verifica si debes revocarlos en GitHub.'
                    ) % {
                        'order': order.name,
                        'user': access.github_username or (
                            access.github_partner_id.name if access.github_partner_id
                            else _('(sin asignar)')
                        ),
                        'repos': repo_names,
                    },
                    user_id=order.user_id.id or self.env.user.id,
                )
        return res

    # ── Subscription lifecycle: pause / churn / reactivation ────────────────

    def write(self, vals):
        """Intercepta cambios de subscription_state para gestionar el ciclo de
        vida de los accesos GitHub:

        - Cualquier estado → 3_progress: crea (o re-crea) registros de acceso.
          Esto cubre: primera activación, re-activación tras pausa/churn.
        - Activo → 4_paused / 6_churn: revoca automáticamente todos los repos
          via GitHub API (por repo) y registra el resultado en el chatter.

        El flujo de suscripción/venta NUNCA se interrumpe: todos los errores
        de GitHub API se capturan internamente y se registran como 'error' en
        cada repo afectado.
        """
        new_sub_state = vals.get('subscription_state')

        if new_sub_state == '3_progress':
            # Capturar las órdenes antes de escribir para detectar transición
            # (desde closed, desde None, desde otro activo — cualquier caso)
            orders_to_activate = self.filtered(
                lambda o: o.subscription_state != '3_progress'
                and o.has_github_connector_lines
            )

        elif new_sub_state in _CLOSED_SUBSCRIPTION_STATES:
            # Capturar órdenes que venían de un estado activo
            orders_to_revoke = self.filtered(
                lambda o: o.subscription_state in _ACTIVE_SUBSCRIPTION_STATES
                and o.has_github_connector_lines
            )

        # ── Ejecutar write primero — suscripción/venta nunca se bloquea ────
        res = super().write(vals)

        if new_sub_state == '3_progress':
            for order in orders_to_activate:
                # Idempotente: crea solo padres/repos que falten
                order._create_github_access_records()

                # Actividad de aviso para repos en pending (usuario ya asignado)
                for access in order.github_access_ids.filtered(
                    lambda a: a.github_username
                    and any(r.github_status == 'pending' for r in a.repo_ids)
                ):
                    repos_pending = access.repo_ids.filtered(
                        lambda r: r.github_status == 'pending'
                    )
                    repo_names = ', '.join(
                        repos_pending.mapped('repository_id.complete_name')
                    )
                    new_state_label = dict(
                        self._fields['subscription_state'].selection
                    ).get(new_sub_state, new_sub_state)
                    access.activity_schedule(
                        'mail.mail_activity_data_todo',
                        summary=_('Suscripción activada — sincronizar accesos GitHub'),
                        note=_(
                            'La suscripción <b>%(order)s</b> cambió a estado '
                            '<b>%(state)s</b>.<br/>'
                            'El usuario <b>%(user)s</b> tiene accesos pendientes:<br/>'
                            '<b>%(repos)s</b><br/><br/>'
                            'Sincroniza los accesos en GitHub.'
                        ) % {
                            'order': order.name,
                            'state': new_state_label,
                            'user': access.github_username,
                            'repos': repo_names,
                        },
                        user_id=order.user_id.id or self.env.user.id,
                    )

        elif new_sub_state in _CLOSED_SUBSCRIPTION_STATES:
            state_label = dict(
                self._fields['subscription_state'].selection
            ).get(new_sub_state, new_sub_state)
            for order in orders_to_revoke:
                self._revoke_github_access_for_order(order, state_label)

        return res

