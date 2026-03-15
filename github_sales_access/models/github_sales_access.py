import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

_STATUS_SELECTION = [
    ('draft', 'Borrador'),
    ('pending', 'Pendiente'),
    ('active', 'Activo'),
    ('inactive', 'Revocado'),
    ('error', 'Error'),
    ('orphan', 'Huérfano ⚠️'),
]

# Peor → mejor (para calcular status del padre)
_STATUS_PRIORITY = {
    'orphan': 0,
    'error': 1,
    'inactive': 2,
    'pending': 3,
    'draft': 4,
    'active': 5,
}

_STATUS_COLORS = {
    'draft': 0,
    'pending': 3,    # orange
    'active': 10,    # green
    'inactive': 1,   # red
    'error': 1,      # red
    'orphan': 6,     # purple
}


class GithubSalesAccess(models.Model):
    """Un registro por (línea de conector GitHub, usuario GitHub).

    Representa el derecho de acceso de un usuario GitHub concreto,
    vinculado a una línea de pedido del producto 'GitHub Connector'.
    Los repositorios a los que tiene acceso viven en los registros
    hijo `github.sales.access.repo`.
    """
    _name = 'github.sales.access'
    _description = 'GitHub Sales Access'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'partner_id, github_partner_id, id'
    _rec_name = 'display_name'

    # ─── Pedido / suscripción ────────────────────────────────────────────────

    order_line_id = fields.Many2one(
        comodel_name='sale.order.line',
        string='Línea de Pedido (Conector)',
        required=False,
        ondelete='cascade',
        index=True,
        domain="[('product_id.is_github_connector', '=', True)]",
        help='Línea del producto GitHub Connector que genera este acceso. '
             'Vacío en registros tipo Huérfano detectados por el cron.',
    )
    order_id = fields.Many2one(
        comodel_name='sale.order',
        string='Pedido',
        related='order_line_id.order_id',
        store=True,
        index=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Cliente',
        related='order_line_id.order_id.partner_id',
        store=True,
        index=True,
        readonly=True,
    )
    order_state = fields.Selection(
        related='order_line_id.order_id.state',
        string='Estado del Pedido',
        store=True,
        readonly=True,
    )

    # ─── Usuario GitHub ──────────────────────────────────────────────────────

    github_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Usuario GitHub (Partner)',
        index=True,
        domain="[('github_name', '!=', False)]",
        help='Partner de Odoo vinculado a la cuenta GitHub del cliente. '
             'Debe tener el campo "GitHub Login" (github_name) completado.',
    )
    github_username = fields.Char(
        string='GitHub Login',
        compute='_compute_github_username',
        store=True,
        readonly=False,
        help='Nombre técnico de usuario en GitHub. '
             'Se rellena automáticamente desde el partner, '
             'pero puede editarse manualmente para orphans.',
    )

    # ─── Repositorios (hijos) ────────────────────────────────────────────────

    repo_ids = fields.One2many(
        comodel_name='github.sales.access.repo',
        inverse_name='access_id',
        string='Repositorios',
    )
    repo_count = fields.Integer(
        string='Repos',
        compute='_compute_repo_count',
    )

    # ─── Estado global (calculado desde hijos) ──────────────────────────────

    github_status = fields.Selection(
        selection=_STATUS_SELECTION,
        string='Estado Global',
        compute='_compute_github_status',
        store=True,
        default='draft',
        index=True,
    )
    color = fields.Integer(
        string='Color',
        compute='_compute_color',
    )

    # ─── Misc ────────────────────────────────────────────────────────────────

    active = fields.Boolean(default=True)
    last_sync_date = fields.Datetime(
        string='Último Sync',
        compute='_compute_last_sync_date',
        store=True,
    )

    # ─── Computed ────────────────────────────────────────────────────────────

    @api.depends('github_partner_id', 'github_partner_id.github_name')
    def _compute_github_username(self):
        for rec in self:
            if rec.github_partner_id and rec.github_partner_id.github_name:
                rec.github_username = rec.github_partner_id.github_name

    @api.depends('github_partner_id', 'github_username',
                 'repo_ids', 'repo_ids.repository_id')
    def _compute_display_name(self):
        for rec in self:
            user = rec.github_username or (
                rec.github_partner_id.name if rec.github_partner_id else _('Sin usuario')
            )
            order = rec.order_id.name if rec.order_id else _('Sin pedido')
            rec.display_name = '%s — %s' % (user, order)

    @api.depends('repo_ids')
    def _compute_repo_count(self):
        for rec in self:
            rec.repo_count = len(rec.repo_ids)

    @api.depends('repo_ids.github_status')
    def _compute_github_status(self):
        for rec in self:
            statuses = rec.repo_ids.mapped('github_status')
            if not statuses:
                rec.github_status = 'draft'
                continue
            # Tomar el peor estado entre todos los hijos
            worst = min(statuses, key=lambda s: _STATUS_PRIORITY.get(s, 5))
            rec.github_status = worst

    @api.depends('github_status')
    def _compute_color(self):
        for rec in self:
            rec.color = _STATUS_COLORS.get(rec.github_status, 0)

    @api.depends('repo_ids.last_sync_date')
    def _compute_last_sync_date(self):
        for rec in self:
            dates = rec.repo_ids.filtered('last_sync_date').mapped('last_sync_date')
            rec.last_sync_date = max(dates) if dates else False

    # ─── Constrains ──────────────────────────────────────────────────────────

    @api.constrains('order_line_id', 'github_partner_id')
    def _check_unique_access(self):
        """Un mismo usuario no puede tener dos accesos activos al mismo conector."""
        for rec in self:
            if not rec.order_line_id or not rec.github_partner_id:
                continue
            duplicate = self.search([
                ('id', '!=', rec.id),
                ('order_line_id', '=', rec.order_line_id.id),
                ('github_partner_id', '=', rec.github_partner_id.id),
                ('active', '=', True),
            ])
            if duplicate:
                raise UserError(_(
                    'El usuario "%s" ya tiene un acceso activo para la línea de pedido "%s".'
                ) % (rec.github_username, rec.order_line_id.name))

    # ─── Actions ─────────────────────────────────────────────────────────────

    def action_open_form(self):
        """Abre la vista formulario de este registro (usado desde la lista editable)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_sync_all_repos(self):
        """Sincroniza todos los repositorios hijo de este acceso en GitHub."""
        for rec in self:
            if not rec.github_username:
                raise UserError(_(
                    'El registro "%s" no tiene usuario GitHub asignado. '
                    'Completa el campo "GitHub Login" antes de sincronizar.'
                ) % rec.display_name)
            rec.repo_ids.action_sync()

    def action_revoke_all_repos(self):
        """Revoca el acceso a todos los repositorios hijo."""
        for rec in self:
            rec.repo_ids.action_revoke()

    # ─── Cron ────────────────────────────────────────────────────────────────

    @api.model
    def cron_sync_active_accesses(self):
        """Cron mensual: re-sincroniza todos los accesos activos."""
        active_repos = self.env['github.sales.access.repo'].search([
            ('github_status', 'not in', ['inactive', 'orphan']),
            ('access_id.github_username', '!=', False),
            ('access_id.order_state', '=', 'sale'),
        ])
        _logger.info('GITHUB ACCESS CRON: Syncing %d repo records.', len(active_repos))
        for repo_rec in active_repos:
            try:
                repo_rec.action_sync()
            except Exception as e:
                _logger.error(
                    'GITHUB ACCESS CRON: Error syncing repo record %d: %s',
                    repo_rec.id, str(e),
                )

    @api.model
    def cron_check_discrepancies(self):
        """Cron semanal: detecta colaboradores en GitHub sin suscripción activa."""
        repos = self.env['github.repository'].search([])
        for repo in repos:
            try:
                self._check_repo_discrepancies(repo)
            except Exception as e:
                _logger.warning(
                    'GITHUB ACCESS CRON: Error checking discrepancies for repo "%s": %s',
                    repo.complete_name, str(e),
                )

    def _check_repo_discrepancies(self, repo):
        """Detecta colaboradores en GitHub que NO tienen repo activo en Odoo.

        Por cada huérfano encontrado, busca o crea un registro padre
        `github.sales.access` y añade una fila hijo con `github_status='orphan'`.
        Si la fila hijo ya existe, solo actualiza la fecha.
        """
        gh_api = repo.get_github_connector()
        gh_repo = gh_api.get_repo(repo.complete_name)
        gh_collaborators = {c.login for c in gh_repo.get_collaborators()}

        # Logins con repos activos en Odoo para este repositorio
        active_usernames = set(
            self.env['github.sales.access.repo'].search([
                ('repository_id', '=', repo.id),
                ('github_status', '=', 'active'),
                ('access_id.order_state', '=', 'sale'),
            ]).mapped('access_id.github_username')
        )

        orphan_logins = gh_collaborators - active_usernames
        if not orphan_logins:
            return

        _logger.warning(
            'GITHUB ACCESS: Repo "%s" has %d orphan(s): %s',
            repo.complete_name, len(orphan_logins), ', '.join(sorted(orphan_logins)),
        )

        RepoLine = self.env['github.sales.access.repo']

        for login in orphan_logins:
            # ¿Ya hay una fila orphan para este login+repo?
            existing_repo_line = RepoLine.search([
                ('repository_id', '=', repo.id),
                ('github_status', '=', 'orphan'),
                ('access_id.github_username', '=', login),
            ], limit=1)
            if existing_repo_line:
                existing_repo_line.last_sync_date = fields.Datetime.now()
                continue

            # Buscar o crear el registro padre para este GitHub login
            github_partner = self.env['res.partner'].search([
                ('github_name', '=', login),
            ], limit=1)

            # ¿Existe ya un access sin order_line (orphan padre) para este login?
            parent = self.search([
                ('github_username', '=', login),
                ('order_line_id', '=', False),
                ('active', '=', True),
            ], limit=1)

            if not parent:
                parent = self.create({
                    'github_partner_id': github_partner.id if github_partner else False,
                    'github_username': login if not github_partner else False,
                })

            # Crear la fila hijo orphan
            orphan_repo_line = RepoLine.create({
                'access_id': parent.id,
                'repository_id': repo.id,
                'github_status': 'orphan',
                'last_sync_date': fields.Datetime.now(),
                'sync_message': _(
                    'Detectado por cron de discrepancias: usuario presente '
                    'en GitHub sin suscripción activa en Odoo.'
                ),
            })

            _logger.info(
                'GITHUB ACCESS: Created orphan repo line (id=%d) for "%s" in "%s".',
                orphan_repo_line.id, login, repo.complete_name,
            )

            parent.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('⚠️ Colaborador huérfano en GitHub'),
                note=_(
                    'El usuario <b>%(user)s</b> tiene acceso al repositorio '
                    '<b>%(repo)s</b> en GitHub pero <b>no tiene suscripción '
                    'activa</b> en Odoo.<br/><br/>'
                    'Opciones:<br/>'
                    '• Si es cliente activo: crea el pedido/acceso y vincula este registro.<br/>'
                    '• Si no lo es: revoca el acceso desde la pestaña de repositorios.'
                ) % {
                    'user': login,
                    'repo': repo.complete_name,
                },
                user_id=self.env.ref('base.user_admin').id,
            )
