import logging

from odoo import _, api, fields, models

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

    @api.depends('order_line.product_id.is_github_connector')
    def _compute_has_github_connector_lines(self):
        for order in self:
            order.has_github_connector_lines = any(
                line.product_id.is_github_connector
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
            lambda l: l.product_id.is_github_connector
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
        for order in self.filtered(lambda o: o.state == 'sale'):
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
        for order in self:
            if order.has_github_connector_lines:
                order._create_github_access_records()
        return res

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
            lambda l: l.product_id.product_tmpl_id.is_github_connector
        )
        if not connector_lines:
            return

        for line in connector_lines:
            tmpl = line.product_id.product_tmpl_id
            repos = tmpl.get_github_repos_for_partner(
                partner=self.partner_id,
                current_order=self,
            )
            if not repos:
                _logger.info(
                    'GITHUB ACCESS: No repos resolved for line %d (order %s). '
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

