import logging

from github.GithubException import GithubException
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Estados de subscription_state que indican una suscripción vigente
_ACTIVE_SUBSCRIPTION_STATES = ('2_renewal', '3_progress', '7_upsell')

_STATUS_SELECTION = [
    ('draft', 'Borrador'),
    ('pending', 'Pendiente'),
    ('active', 'Activo'),
    ('revoke', 'Revocado ✕'),     # revocación automática por suscripción
    ('inactive', 'Inactivo'),   # revocación manual
    ('error', 'Error'),
    ('orphan', 'Huérfano ⚠️'),
]

# Peor → mejor (para calcular status del padre)
_STATUS_PRIORITY = {
    'orphan': 0,
    'error': 1,
    'revoke': 2,     # automático — peor que error porque requiere revisión
    'inactive': 3,   # manual — esperado, ya revisado
    'pending': 4,
    'draft': 5,
    'active': 6,
}

_STATUS_COLORS = {
    'draft': 0,
    'pending': 3,    # orange
    'active': 10,    # green
    'revoke': 9,     # dark red (revocación automática)
    'inactive': 1,   # red (revocación manual)
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
        domain="[('product_id.product_tmpl_id.github_product_type', '=', 'connector')]",
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
        related='order_line_id.order_id.subscription_state',
        string='Estado Suscripción',
        store=True,
        readonly=True,
    )
    order_sale_state = fields.Selection(
        related='order_line_id.order_id.state',
        string='Estado Pedido',
        store=False,
        readonly=True,
    )

    # ─── Usuario GitHub ──────────────────────────────────────────────────────

    github_partner_id = fields.Char(
        string='Usuario GitHub',
        help='Nombre o alias que el usuario tiene en GitHub (ej. "Fernando"). '
             'Se rellena automáticamente al detectar el acceso.',
    )
    github_username = fields.Char(
        string='GitHub Login',
        index=True,
        help='Nombre técnico de usuario en GitHub (ej. "GanemoCorp"). '
             'Es el identificador que se usa en la API de GitHub.',
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

    @api.depends('github_partner_id', 'github_username',
                 'repo_ids', 'repo_ids.repository_id')
    def _compute_display_name(self):
        for rec in self:
            user = rec.github_partner_id or rec.github_username or _('Sin usuario')
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

    @api.constrains('order_line_id', 'github_username')
    def _check_unique_access(self):
        """Un mismo usuario no puede tener dos accesos activos al mismo conector."""
        for rec in self:
            if not rec.order_line_id or not rec.github_username:
                continue
            duplicate = self.search([
                ('id', '!=', rec.id),
                ('order_line_id', '=', rec.order_line_id.id),
                ('github_username', '=', rec.github_username),
                ('active', '=', True),
            ])
            if duplicate:
                raise UserError(_(
                    'El usuario "%s" ya tiene un acceso activo para la línea de pedido "%s".'
                ) % (rec.github_username, rec.order_line_id.name))

    # ─── ORM overrides ──────────────────────────────────────────────────────

    def write(self, vals):
        """Dispara actividad de aviso cuando el registro transiciona a 'orphan'.

        La actividad se crea exactamente una vez: cuando github_status cambia
        de cualquier otro estado a 'orphan'.  Si el registro ya era 'orphan'
        no se vuelve a crear.
        """
        if 'github_status' not in vals:
            return super().write(vals)

        # Capturar estados previos antes de escribir
        prev_statuses = {rec.id: rec.github_status for rec in self}
        result = super().write(vals)

        new_status = vals['github_status']
        if new_status != 'orphan':
            return result

        for rec in self:
            if prev_statuses.get(rec.id) != 'orphan':
                rec.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_('\u26a0\ufe0f Acceso hu\u00e9rfano detectado en GitHub'),
                    note=_(
                        'El usuario <b>%(user)s</b> tiene acceso a uno o m\u00e1s '
                        'repositorios en GitHub <b>sin suscripci\u00f3n activa</b> '
                        'en Odoo.<br/><br/>'
                        'Revisa los repositorios en la pesta\u00f1a "Repositorios" '
                        'y decide:<br/>'
                        '\u2022 Si es cliente activo: vincula el acceso a su pedido.<br/>'
                        '\u2022 Si no lo es: revoca el acceso desde la pesta\u00f1a de repositorios.'
                    ) % {'user': rec.github_username or rec.display_name},
                    user_id=self.env.ref('base.user_admin').id,
                )
        return result

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
            ('access_id.order_state', 'in', _ACTIVE_SUBSCRIPTION_STATES),
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
        """Cron semanal: detecta colaboradores en GitHub sin suscripción activa.

        Optimizado: 2 HTTP calls por organización independientemente del número de
        repositorios (antes: 2 calls × N repos = 510 calls para 255 repos).
        """
        orgs = self.env['github.organization'].search([])
        if not orgs:
            _logger.info('GITHUB ACCESS CRON: No organizations found, skipping discrepancy check.')
            return
        for org in orgs:
            # Pre-verificar si hay token antes de llamar la API.
            # get_github_connector() lanza UserError si no hay token — en ese
            # caso es comportamiento esperado y no debe emitir un WARNING.
            if not self.env['abstract.github.model'].get_github_token():
                _logger.info(
                    'GITHUB ACCESS CRON: No GitHub token configured in Settings, skipping all orgs.',
                )
                break
            try:
                self._check_org_discrepancies(org)
            except Exception as e:
                _logger.warning(
                    'GITHUB ACCESS CRON: Error checking discrepancies for org "%s": %s',
                    org.github_name, str(e),
                )

    def _check_org_discrepancies(self, org):
        """Detecta colaboradores EXTERNOS en GitHub que NO tienen suscripción activa en Odoo.

        Realiza solo 2 HTTP calls independientemente del número de repos:
          - gh_org.get_outside_collaborators() → todos los externos de la org
          - gh_org.get_pending_invites()        → todas las invitaciones pendientes

        Los Members (empleados de la organización) se excluyen explícitamente
        porque tienen acceso como miembros de la org y no necesitan suscripción.

        Los huérfanos nuevos se crean SIN repo_ids. El usuario puede completar
        los repos después con la acción 'Rellenar repos de huérfanos' o el botón
        '🔍 Detectar repos en GitHub' desde el formulario del acceso.
        """
        gh_api = org.get_github_connector()
        gh_org = gh_api.get_organization(org.github_name)

        # ── 1ª HTTP call: outside collaborators de TODA la org ──────────────────
        try:
            outside_collaborators = list(gh_org.get_outside_collaborators())
        except GithubException as e:
            if e.status == 403:
                raise UserError(_(
                    'El token de GitHub no tiene permisos suficientes para '
                    'consultar los colaboradores de la organización "%s".\n\n'
                    'El token necesita el scope: admin:org o read:org.\n'
                    'Detalle: %s'
                ) % (org.github_name, e.data.get('message', str(e))))
            raise
        outside_logins = {c.login for c in outside_collaborators}
        # Mapa login → display name (c.name puede ser None si el usuario no lo configuró)
        github_display_names = {c.login: (c.name or c.login) for c in outside_collaborators}

        # ── 2ª HTTP call: invitaciones pendientes de TODA la org ────────────────
        pending_logins = set()
        try:
            pending_invites = list(gh_org.get_pending_invites())
            pending_logins = {inv.login for inv in pending_invites if inv.login}
            # Display names de invitados (a veces name viene como None)
            github_display_names.update({
                inv.login: (inv.name or inv.login)
                for inv in pending_invites if inv.login
            })
        except Exception as e:
            _logger.info(
                'GITHUB ACCESS: Could not fetch pending invites for org "%s" '
                '(may not be available on this GitHub plan): %s',
                org.github_name, str(e),
            )

        # Universo a auditar: externos + invitados pendientes de toda la org
        gh_collaborators = outside_logins | pending_logins
        if not gh_collaborators:
            _logger.info(
                'GITHUB ACCESS CRON: Org "%s" has no outside collaborators or pending invites.',
                org.github_name,
            )
            return

        _logger.info(
            'GITHUB ACCESS CRON: Org "%s" — %d outside collaborators + %d pending invites.',
            org.github_name, len(outside_logins), len(pending_logins),
        )

        # ── Query 1 (batch): logins ya cubiertos por repos activos/pending ──────
        # Se considera cualquier repo de esta org (no solo uno)
        org_repo_ids = self.env['github.repository'].search([
            ('organization_id', '=', org.id),
        ]).ids

        known_usernames = set(
            self.env['github.sales.access.repo'].search([
                ('repository_id', 'in', org_repo_ids),
                ('github_status', 'in', ('active', 'pending')),
                ('access_id.order_state', 'in', _ACTIVE_SUBSCRIPTION_STATES),
            ]).mapped('access_id.github_username')
        ) if org_repo_ids else set()

        orphan_logins = gh_collaborators - known_usernames
        if not orphan_logins:
            _logger.info(
                'GITHUB ACCESS CRON: Org "%s" — no orphans detected.',
                org.github_name,
            )
            return

        _logger.info(
            'GITHUB ACCESS CRON: Org "%s" — %d orphan(s) detected: %s',
            org.github_name, len(orphan_logins), ', '.join(sorted(orphan_logins)),
        )

        # ── Query 2 (batch): padres huérfanos ya existentes → solo refrescar ────
        existing_orphan_parents = {}
        existing_parents_all = self.search([
            ('github_username', 'in', list(orphan_logins)),
            ('active', '=', True),
        ])
        _priority = {s: i + 1 for i, s in enumerate(_ACTIVE_SUBSCRIPTION_STATES)
                     if s != '3_progress'}
        _priority['3_progress'] = 0  # 3_progress tiene la mayor prioridad (0)
        for rec in existing_parents_all:
            login = rec.github_username
            if login not in existing_orphan_parents:
                existing_orphan_parents[login] = rec
            else:
                current_best = existing_orphan_parents[login]
                rec_state = rec.order_line_id.order_id.subscription_state if rec.order_line_id else False
                best_state = current_best.order_line_id.order_id.subscription_state if current_best.order_line_id else False
                if _priority.get(rec_state, 99) < _priority.get(best_state, 99):
                    existing_orphan_parents[login] = rec

        now = fields.Datetime.now()
        sync_msg = _(
            'Detectado por cron de discrepancias (org-level): usuario presente '
            'en GitHub sin suscripción activa en Odoo.'
        )

        # ── Bucle final: crear o refrescar registros padre sin repo_ids ──────────
        for login in orphan_logins:
            parent = existing_orphan_parents.get(login)

            if parent:
                # Registro ya existe → solo actualizar sync_date si ya es huérfano
                already_orphan_repos = parent.repo_ids.filtered(
                    lambda r: r.github_status == 'orphan'
                )
                if already_orphan_repos:
                    already_orphan_repos.write({'last_sync_date': now})
                    continue
                # Tiene padre pero sin fila orphan → se marca implícitamente
                # al crear repo_ids con orphan status (si ya tiene repos, no tocar)
                # En este caso no forzamos nada: el padre existe y será visible
                _logger.info(
                    'GITHUB ACCESS: Orphan "%s" has existing parent (id=%d) without orphan repo lines.',
                    login, parent.id,
                )
            else:
                # No hay padre → crear registro nuevo (sin repo_ids por ahora)
                parent = self.create({
                    'github_username': login,
                    'github_partner_id': github_display_names.get(login) or login,
                })
                # Forzar github_status a 'orphan' para que la actividad de aviso se dispare
                # (normalmente lo haría _compute_github_status via los repo_ids,
                # pero como los repo_ids quedan vacíos lo escribimos directamente)
                parent.write({'github_status': 'orphan'})
                _logger.info(
                    'GITHUB ACCESS: Created orphan parent (id=%d) for "%s" (no repo lines yet).',
                    parent.id, login,
                )

    def _check_repo_discrepancies(self, repo):
        """DEPRECADO. Detecta huérfanos por repositorio individual (2 HTTP calls/repo).

        Usar _check_org_discrepancies en su lugar (2 calls para toda la org).
        Este método se mantiene por compatibilidad con tests existentes.
        """
        _logger.info(
            'GITHUB ACCESS: _check_repo_discrepancies is deprecated. '
            'Use _check_org_discrepancies instead (called for repo "%s").',
            repo.complete_name,
        )
        gh_api = repo.get_github_connector()
        gh_repo = gh_api.get_repo(repo.complete_name)

        outside_collaborators = list(gh_repo.get_collaborators(affiliation='outside'))
        outside_logins = {c.login for c in outside_collaborators}
        github_display_names = {c.login: (c.name or c.login) for c in outside_collaborators}

        pending_logins = set()
        try:
            pending_invitations = list(gh_repo.get_pending_invitations())
            pending_logins = {inv.invitee.login for inv in pending_invitations if inv.invitee}
            github_display_names.update({
                inv.invitee.login: (inv.invitee.name or inv.invitee.login)
                for inv in pending_invitations if inv.invitee
            })
        except Exception as e:
            _logger.info(
                'GITHUB ACCESS: Could not fetch pending invitations for repo "%s": %s',
                repo.complete_name, str(e),
            )

        gh_collaborators = outside_logins | pending_logins

        known_usernames = set(
            self.env['github.sales.access.repo'].search([
                ('repository_id', '=', repo.id),
                ('github_status', 'in', ('active', 'pending')),
                ('access_id.order_state', 'in', _ACTIVE_SUBSCRIPTION_STATES),
            ]).mapped('access_id.github_username')
        )

        orphan_logins = gh_collaborators - known_usernames
        if not orphan_logins:
            return

        _logger.info(
            'GITHUB ACCESS: Repo "%s" has %d orphan(s): %s',
            repo.complete_name, len(orphan_logins), ', '.join(sorted(orphan_logins)),
        )

        existing_orphan_lines = self.env['github.sales.access.repo'].search([
            ('repository_id', '=', repo.id),
            ('github_status', '=', 'orphan'),
            ('access_id.github_username', 'in', list(orphan_logins)),
        ])
        already_orphaned = {
            line.access_id.github_username: line
            for line in existing_orphan_lines
        }

        new_logins = orphan_logins - set(already_orphaned.keys())
        existing_parents = {}
        if new_logins:
            _priority = {s: i + 1 for i, s in enumerate(_ACTIVE_SUBSCRIPTION_STATES)
                         if s != '3_progress'}
            _priority['3_progress'] = 0
            all_candidates = self.search([
                ('github_username', 'in', list(new_logins)),
                ('active', '=', True),
            ])
            for rec in all_candidates:
                login = rec.github_username
                if login not in existing_parents:
                    existing_parents[login] = rec
                else:
                    current_best = existing_parents[login]
                    if _priority.get(rec.order_state, 99) < _priority.get(current_best.order_state, 99):
                        existing_parents[login] = rec

        now = fields.Datetime.now()
        sync_msg = _(
            'Detectado por cron de discrepancias: usuario presente '
            'en GitHub sin suscripción activa en Odoo.'
        )
        RepoLine = self.env['github.sales.access.repo']

        for login in orphan_logins:
            if login in already_orphaned:
                already_orphaned[login].last_sync_date = now
                continue

            parent = existing_parents.get(login)
            if not parent:
                parent = self.create({
                    'github_username': login,
                    'github_partner_id': github_display_names.get(login) or login,
                })

            orphan_repo_line = RepoLine.create({
                'access_id': parent.id,
                'repository_id': repo.id,
                'github_status': 'orphan',
                'last_sync_date': now,
                'sync_message': sync_msg,
            })
            _logger.info(
                'GITHUB ACCESS: Created orphan repo line (id=%d) for "%s" in "%s".',
                orphan_repo_line.id, login, repo.complete_name,
            )

    _FILL_ORPHAN_GRAPHQL = """
        query OrphanRepos($org: String!, $login: String!, $cursor: String) {
          organization(login: $org) {
            repositories(
              first: 100
              after: $cursor
              affiliations: [OWNER]
              orderBy: {field: NAME, direction: ASC}
            ) {
              pageInfo { hasNextPage endCursor }
              nodes {
                name
                nameWithOwner
                collaborators(affiliation: OUTSIDE, query: $login) {
                  nodes { login }
                }
              }
            }
          }
        }
    """

    def action_fill_orphan_repos(self):
        """Detecta en qué repositorios de GitHub está cada usuario seleccionado.

        Consulta en GitHub todos los repos de la organización donde ese usuario es
        colaborador externo. Si encuentra repositorios a los que el usuario tiene
        acceso pero no están registrados en sus líneas, los añade como huérfanos.
        
        Puede invocarse:
          - Como server action masivo desde la lista.
          - Desde el botón '🔍 Detectar repos en GitHub' en el formulario.
        """
        targets_with_login = self.filtered(lambda r: r.github_username)
        if not targets_with_login:
            return

        orgs = self.env['github.organization'].search([])
        if not orgs:
            return

        # Mapa complete_name → repo Odoo (para lookup sin búsqueda BD por repo)
        all_repos = self.env['github.repository'].search([])
        repo_by_name = {r.complete_name: r for r in all_repos}

        now = fields.Datetime.now()
        sync_msg = _(
            'Detectado por acción "Rellenar repos de huérfanos": '
            'usuario con acceso directo al repositorio sin suscripción activa.'
        )
        RepoLine = self.env['github.sales.access.repo']

        for parent in targets_with_login:
            login = parent.github_username

            for org in orgs:
                org_name = org.github_name
                if not org_name:
                    continue

                # Paginar: recorrer todos los repos de la org (máx 100 por página)
                cursor = None
                has_next = True
                while has_next:
                    variables = {"org": org_name, "login": login, "cursor": cursor}
                    try:
                        data = parent.env['abstract.github.model'].graphql_query(
                            self._FILL_ORPHAN_GRAPHQL, variables
                        )
                    except Exception as e:
                        _logger.warning(
                            'GITHUB ACCESS fill_orphan: GraphQL error for orphan "%s" '
                            'in org "%s": %s',
                            login, org_name, str(e),
                        )
                        break

                    org_data = (data or {}).get('organization') or {}
                    repos_page = org_data.get('repositories') or {}
                    page_info = repos_page.get('pageInfo', {})
                    has_next = page_info.get('hasNextPage', False)
                    cursor = page_info.get('endCursor')

                    for repo_node in repos_page.get('nodes', []):
                        # collaborators devuelve solo los que coinciden con el query login
                        collab_logins = {
                            c['login']
                            for c in (repo_node.get('collaborators') or {}).get('nodes', [])
                        }
                        if login not in collab_logins:
                            continue

                        full_name = repo_node.get('nameWithOwner', '')
                        repo = repo_by_name.get(full_name)
                        if not repo:
                            # Repo existe en GitHub pero no registrado en Odoo — omitir
                            continue

                        already_exists = RepoLine.search([
                            ('access_id', '=', parent.id),
                            ('repository_id', '=', repo.id),
                        ], limit=1)
                        if already_exists:
                            already_exists.write({'last_sync_date': now})
                            continue

                        RepoLine.create({
                            'access_id': parent.id,
                            'repository_id': repo.id,
                            'github_status': 'orphan',
                            'last_sync_date': now,
                            'sync_message': sync_msg,
                        })
                        _logger.info(
                            'GITHUB ACCESS fill_orphan: Added repo "%s" to orphan "%s" '
                            '(parent id=%d).',
                            full_name, login, parent.id,
                        )


    def _find_or_create_orphan_parent(self, login, github_partner, github_display_name=None):
        """Busca o crea el registro padre para un login huérfano.

        Prioridad:
          1. Suscripción en progreso (3_progress)
          2. Cualquier estado activo (_ACTIVE_SUBSCRIPTION_STATES)
          3. Cualquier registro existente con ese login
          4. Crear nuevo registro

        Nota: _check_repo_discrepancies usa lógica batch equivalente.
        Este método existe para uso unitario (tests y llamadas individuales).
        """
        _priority = {s: i + 1 for i, s in enumerate(_ACTIVE_SUBSCRIPTION_STATES)
                     if s != '3_progress'}
        _priority['3_progress'] = 0  # 3_progress tiene la mayor prioridad (0)

        candidates = self.search([
            ('github_username', '=', login),
            ('active', '=', True),
        ])

        if candidates:
            # Leer subscription_state desde la sale.order directamente
            # (no depender del campo stored order_state que puede estar desactualizado)
            def _state(rec):
                order = rec.order_line_id.order_id
                sub_state = order.subscription_state if order else False
                return _priority.get(sub_state, 99)
            return min(candidates, key=_state)

        return self.create({
            'github_username': login,
            'github_partner_id': github_display_name or login,
        })
