import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

_REPO_STATUS_SELECTION = [
    ('draft', 'Borrador'),
    ('pending', 'Pendiente'),
    ('active', 'Activo'),
    ('revoke', 'Revocado ✕'),     # revocación automática por cambio de suscripción
    ('inactive', 'Inactivo'),   # revocación manual vía botón
    ('error', 'Error'),
    ('orphan', 'Huérfano ⚠️'),
]


class GithubSalesAccessRepo(models.Model):
    """Un registro por (acceso padre, repositorio).

    Representa el acceso concreto de un usuario GitHub a un repositorio
    específico. El sync y el revoke operan a este nivel.
    """
    _name = 'github.sales.access.repo'
    _description = 'GitHub Sales Access — Repositorio'
    _order = 'access_id, repository_id'
    _rec_name = 'display_name'

    # ─── Relación con el padre ───────────────────────────────────────────────

    access_id = fields.Many2one(
        comodel_name='github.sales.access',
        string='Acceso',
        required=True,
        ondelete='cascade',
        index=True,
    )

    # ─── Repositorio ──────────────────────────────────────────────────────────

    repository_id = fields.Many2one(
        comodel_name='github.repository',
        string='Repositorio',
        required=True,
        index=True,
    )

    # ─── Estado ───────────────────────────────────────────────────────────────

    github_status = fields.Selection(
        selection=_REPO_STATUS_SELECTION,
        string='Estado',
        default='draft',
        required=True,
        index=True,
    )
    last_sync_date = fields.Datetime(
        string='Último Sync',
        readonly=True,
    )
    sync_message = fields.Text(
        string='Resultado del Sync',
        readonly=True,
    )

    # ─── Computed ─────────────────────────────────────────────────────────────

    @api.depends('access_id.github_username', 'repository_id.name')
    def _compute_display_name(self):
        for rec in self:
            user = rec.access_id.github_username or '?'
            repo = rec.repository_id.name or '?'
            rec.display_name = '%s → %s' % (user, repo)

    # ─── Constrains ───────────────────────────────────────────────────────────

    @api.constrains('access_id', 'repository_id')
    def _check_unique_repo_per_access(self):
        """Un acceso no puede tener dos filas para el mismo repositorio."""
        for rec in self:
            duplicate = self.search([
                ('id', '!=', rec.id),
                ('access_id', '=', rec.access_id.id),
                ('repository_id', '=', rec.repository_id.id),
            ])
            if duplicate:
                raise Exception(
                    'El acceso ya tiene una fila para el repositorio "%s".'
                    % rec.repository_id.complete_name
                )

    # ─── Acciones (sync / revoke) ─────────────────────────────────────────────

    def action_sync(self):
        """Añade al usuario como colaborador en el repositorio en GitHub."""
        for rec in self:
            rec._do_sync()

    def _do_sync(self):
        self.ensure_one()
        username = self.access_id.github_username
        if not username:
            self.write({
                'github_status': 'error',
                'sync_message': _('El acceso padre no tiene usuario GitHub asignado.'),
            })
            return

        try:
            gh_api = self.repository_id.get_github_connector()
            gh_repo = gh_api.get_repo(self.repository_id.complete_name)
            gh_repo.add_to_collaborators(username)
            _logger.info(
                'GITHUB ACCESS: Synced "%s" → "%s".',
                username, self.repository_id.complete_name,
            )
            self.write({
                'github_status': 'active',
                'last_sync_date': fields.Datetime.now(),
                'sync_message': _('Acceso sincronizado correctamente.'),
            })
        except Exception as e:
            error_msg = str(e)
            _logger.warning(
                'GITHUB ACCESS: Sync failed "%s" → "%s": %s',
                username, self.repository_id.complete_name, error_msg,
            )
            self.write({
                'github_status': 'error',
                'last_sync_date': fields.Datetime.now(),
                'sync_message': error_msg,
            })
            self.access_id.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('⚠️ Error al sincronizar acceso GitHub'),
                note=_(
                    'No se pudo añadir a <b>%(user)s</b> como colaborador '
                    'en <b>%(repo)s</b>.<br/>Motivo: %(error)s<br/><br/>'
                    'Por favor gestiona el acceso manualmente en GitHub.'
                ) % {
                    'user': username,
                    'repo': self.repository_id.complete_name,
                    'error': error_msg,
                },
                user_id=self.access_id.order_id.user_id.id or self.env.user.id,
            )

    def action_auto_revoke(self, reason=''):
        """Punto de entrada para la revocación AUTOMÁTICA disparada por cambio
        de subscription_state (4_paused o 6_churn).

        A diferencia de action_revoke() (manual), este método:
        - Usa el estado 'revoke' (no 'inactive') para distinguir el origen.
        - Soporta el caso pending (Opción B): marca 'revoke' sin llamar a GitHub.
        - Registra el resultado en el chatter del acceso padre.
        - NUNCA lanza excepción al exterior (el flujo de suscripción no se corta).

        :param reason: Etiqueta del estado de suscripción que disparó la revocación.
        """
        for rec in self:
            rec._do_auto_revoke(reason=reason)

    def _do_auto_revoke(self, reason=''):
        """Lógica interna de revocación automática por repo."""
        self.ensure_one()

        now = fields.Datetime.now()
        username = self.access_id.github_username
        repo_name = self.repository_id.complete_name

        # ── Caso A: repo ya en estado terminal — idempotente ────────────────
        if self.github_status in ('revoke', 'inactive', 'error'):
            return

        # ── Caso B: repo en pending — nunca estuvo activo en GitHub ────────
        if self.github_status in ('draft', 'pending') or not username:
            msg = _(
                'Suscripción cambiada a <b>%(reason)s</b>.<br/>'
                'El repositorio <b>%(repo)s</b> estaba en estado '  \
                '<b>%(status)s</b> — sin acceso previo en GitHub.<br/>'
                'Marcado como <b>Revocado</b> sin llamar a la API.'
            ) % {
                'reason': reason or _('(estado cerrado)'),
                'repo': repo_name,
                'status': dict(_REPO_STATUS_SELECTION).get(self.github_status, self.github_status),
            }
            self.write({
                'github_status': 'revoke',
                'last_sync_date': now,
                'sync_message': msg,
            })
            self.access_id.message_post(
                body=_('🔴 Sin llamada a API — %(repo)s: era %(status)s, marcado Revocado.') % {
                    'repo': repo_name,
                    'status': dict(_REPO_STATUS_SELECTION).get(
                        self.github_status, self.github_status
                    ),
                },
                subtype_xmlid='mail.mt_note',
            )
            return

        # ── Caso C: repo activo — llamar a GitHub API ──────────────────────
        try:
            gh_api = self.repository_id.get_github_connector()
            gh_repo = gh_api.get_repo(repo_name)
            gh_repo.remove_from_collaborators(username)
            _logger.info(
                'GITHUB ACCESS AUTO-REVOKE: "%s" removed from "%s" (reason: %s).',
                username, repo_name, reason,
            )
            self.write({
                'github_status': 'revoke',
                'last_sync_date': now,
                'sync_message': _('Revocado automáticamente: %(reason)s.') % {
                    'reason': reason,
                },
            })
            self.access_id.message_post(
                body=_('✅ Acceso revocado automáticamente en GitHub.<br/>'
                       'Repositorio: <b>%(repo)s</b><br/>'
                       'Motivo: <b>%(reason)s</b>') % {
                    'repo': repo_name,
                    'reason': reason or _('cambio de suscripción'),
                },
                subtype_xmlid='mail.mt_note',
            )
        except UserError as exc:
            # UserError: expected configuration error (e.g. token not set).
            # Log as INFO — this is not an unexpected system failure.
            error_msg = str(exc)
            _logger.info(
                'GITHUB ACCESS AUTO-REVOKE SKIPPED: "%s" from "%s": %s',
                username, repo_name, error_msg,
            )
            self.write({
                'github_status': 'error',
                'last_sync_date': now,
                'sync_message': error_msg,
            })
            self.access_id.message_post(
                body=_('❌ Error al revocar acceso en GitHub.<br/>'
                       'Repositorio: <b>%(repo)s</b><br/>'
                       'Motivo clausura: <b>%(reason)s</b><br/>'
                       'Error: %(error)s<br/><br/>'
                       'Gestiona la revocación manualmente en GitHub.') % {
                    'repo': repo_name,
                    'reason': reason or _('cambio de suscripción'),
                    'error': error_msg,
                },
                subtype_xmlid='mail.mt_note',
            )
            # Error NO se re-lanza — el flujo de suscripción debe continuar
        except Exception as exc:
            error_msg = str(exc)
            _logger.warning(
                'GITHUB ACCESS AUTO-REVOKE FAILED: "%s" from "%s": %s',
                username, repo_name, error_msg,
            )
            self.write({
                'github_status': 'error',
                'last_sync_date': now,
                'sync_message': error_msg,
            })
            self.access_id.message_post(
                body=_('❌ Error al revocar acceso en GitHub.<br/>'
                       'Repositorio: <b>%(repo)s</b><br/>'
                       'Motivo clausura: <b>%(reason)s</b><br/>'
                       'Error: %(error)s<br/><br/>'
                       'Gestiona la revocación manualmente en GitHub.') % {
                    'repo': repo_name,
                    'reason': reason or _('cambio de suscripción'),
                    'error': error_msg,
                },
                subtype_xmlid='mail.mt_note',
            )
            # Error NO se re-lanza — el flujo de suscripción debe continuar

    def action_revoke(self):
        """Elimina al usuario como colaborador del repositorio en GitHub."""
        for rec in self:
            rec._do_revoke()

    def _do_revoke(self):
        self.ensure_one()
        username = self.access_id.github_username
        if not username:
            self.github_status = 'inactive'
            return

        try:
            gh_api = self.repository_id.get_github_connector()
            gh_repo = gh_api.get_repo(self.repository_id.complete_name)
            gh_repo.remove_from_collaborators(username)
            _logger.info(
                'GITHUB ACCESS: Revoked "%s" from "%s".',
                username, self.repository_id.complete_name,
            )
            self.write({
                'github_status': 'inactive',
                'last_sync_date': fields.Datetime.now(),
                'sync_message': _('Acceso revocado el %s.') % fields.Datetime.now(),
            })
        except Exception as e:
            error_msg = str(e)
            _logger.warning(
                'GITHUB ACCESS: Revoke failed "%s" from "%s": %s',
                username, self.repository_id.complete_name, error_msg,
            )
            self.write({
                'github_status': 'error',
                'last_sync_date': fields.Datetime.now(),
                'sync_message': error_msg,
            })
            self.access_id.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('⚠️ Error al revocar acceso GitHub'),
                note=_(
                    'No se pudo revocar a <b>%(user)s</b> del repositorio '
                    '<b>%(repo)s</b>.<br/>Motivo: %(error)s<br/><br/>'
                    'Por favor gestiona la revocación manualmente en GitHub.'
                ) % {
                    'user': username,
                    'repo': self.repository_id.complete_name,
                    'error': error_msg,
                },
                user_id=self.access_id.order_id.user_id.id or self.env.user.id,
            )
