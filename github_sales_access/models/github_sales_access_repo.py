import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

_REPO_STATUS_SELECTION = [
    ('draft', 'Borrador'),
    ('pending', 'Pendiente'),
    ('active', 'Activo'),
    ('inactive', 'Revocado'),
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
