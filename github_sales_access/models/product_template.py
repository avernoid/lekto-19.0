import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

_REPOS_DEFAULT_MODE = [
    ('list', 'Lista fija de repositorios'),
    ('order_lines', 'Basado en módulos comprados por el cliente'),
]

_GITHUB_PRODUCT_TYPE = [
    ('connector', 'GitHub Connector'),
    ('maintenance_fee', 'Fee de Mantenimiento'),
]


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # ── Top-level toggle ─────────────────────────────────────────────────────

    is_github_sync = fields.Boolean(
        string='GitHub Sync',
        default=False,
        help=(
            'Activa la configuración GitHub Sync para este producto. '
            'Al estar marcado, aparecerá la pestaña "GitHub Sync" con '
            'opciones para configurar si este producto otorga acceso a '
            'repositorios (conector) o si cubre el mantenimiento de un '
            'repositorio (fee de mantenimiento).'
        ),
    )

    # ── Product type inside the tab ──────────────────────────────────────────

    github_product_type = fields.Selection(
        selection=_GITHUB_PRODUCT_TYPE,
        string='Tipo de Producto GitHub',
        help=(
            'Define el rol de este producto dentro del flujo GitHub Sync:\n\n'
            '• GitHub Connector: el cliente adquiere un "slot" de acceso '
            'GitHub. Da derecho a un usuario GitHub dentro de la organización.\n'
            '• Fee de Mantenimiento: cubre el mantenimiento de uno o varios '
            'repositorios. Para que un repositorio se añada automáticamente al '
            'acceso GitHub del cliente, DEBEN cumplirse las tres condiciones: '
            '(1) tener contratado el módulo correspondiente, '
            '(2) tener contratado este fee de mantenimiento con dicho '
            'repositorio en estado "En progreso", y '
            '(3) tener contratado un GitHub Connector activo.'
        ),
    )

    # ── Computed boolean shortcuts REMOVED ───────────────────────────────────
    # is_github_connector and is_maintenance_fee are NO LONGER separate fields.
    # Use github_product_type == 'connector' and == 'maintenance_fee' directly.
    # ────────────────────────────────────────────────────────────────────

    # ── Connector-specific fields ────────────────────────────────────────────

    repos_default_mode = fields.Selection(
        selection=_REPOS_DEFAULT_MODE,
        string='Modo de asignación de repositorios',
        default='list',
        help=(
            'Define cómo se determina el listado de repositorios candidatos '
            'cuando se crea un acceso GitHub automáticamente:\n\n'
            '• Lista fija: usa los repositorios indicados en "Repositorios '
            'Incluidos".\n'
            '• Basado en módulos comprados: busca en todos los pedidos '
            'confirmados del cliente (incluyendo el pedido actual) los '
            'productos que tienen una rama GitHub vinculada y extrae su '
            'repositorio.\n\n'
            'Nota: independientemente del modo elegido, solo se añadirán al '
            'acceso GitHub los repositorios que además estén cubiertos por un '
            '"Fee de Mantenimiento" activo del cliente (suscripción en progreso).'
        ),
    )
    github_repository_ids = fields.Many2many(
        comodel_name='github.repository',
        relation='product_template_github_repository_rel',
        column1='product_template_id',
        column2='repository_id',
        string='Repositorios',
    )

    # ── Compute ──────────────────────────────────────────────────────────────

    # The _compute_github_product_flags method has been removed as per instructions.

    # ── Constraint ───────────────────────────────────────────────────────────

    @api.constrains('github_product_type', 'is_github_sync')
    def _check_github_product_type_requires_sync(self):
        for tmpl in self:
            if tmpl.github_product_type and not tmpl.is_github_sync:
                raise UserError(_(
                    'No puedes seleccionar un tipo de producto GitHub sin activar '
                    'primero la opción "GitHub Sync" en la parte superior.'
                ))

    # ── Auto-migration for existing connector products ────────────────────────

    def _auto_init(self):
        """Migrate existing is_github_connector=True products to use the new
        github_product_type='connector' and is_github_sync=True fields.

        This runs on module install/upgrade before the ORM recalculates
        computed fields, ensuring backward compatibility with existing data.
        """
        res = super()._auto_init()
        # Only runs if the old column still has data (pre-upgrade)
        try:
            self.env.cr.execute("""
                UPDATE product_template
                SET is_github_sync = TRUE,
                    github_product_type = 'connector'
                WHERE id IN (
                    SELECT id FROM product_template
                    WHERE (github_product_type IS NULL OR github_product_type = '')
                      AND id IN (
                          SELECT product_tmpl_id FROM product_product pp
                          JOIN sale_order_line sol ON sol.product_id = pp.id
                          JOIN github_sales_access gsa ON gsa.order_line_id = sol.id
                          LIMIT 1
                      )
                )
            """)
        except Exception:
            # Table may not exist yet on fresh install — safe to ignore
            pass
        return res

    # ── Helper ───────────────────────────────────────────────────────────────

    def get_github_repos_for_partner(self, partner, current_order=None):
        """Returns the github.repository candidate set for this connector product.

        This determines the CANDIDATE repos based on repos_default_mode.
        The actual repos added to the access record are further filtered by
        the maintenance fee condition in _create_github_access_records().

        :param partner: res.partner — the order partner
        :param current_order: sale.order — the current order (included even if
               not yet confirmed, to cover the confirmation moment)
        :return: recordset of github.repository without duplicates
        """
        self.ensure_one()

        if self.repos_default_mode == 'list':
            return self.github_repository_ids

        # ── Mode: order_lines ─────────────────────────────────────────────
        # 1. Search all confirmed orders for this partner
        domain = [
            ('order_id.partner_id', '=', partner.id),
            ('order_id.state', '=', 'sale'),
            ('product_id.github_branch_id', '!=', False),
        ]
        lines = self.env['sale.order.line'].search(domain)

        # 2. Include lines from current order (may not be in state='sale' yet)
        if current_order:
            current_lines = current_order.order_line.filtered(
                lambda l: l.product_id.github_branch_id
            )
            lines |= current_lines

        # 3. Extract repos — mapped() returns a deduplicated recordset
        repos = lines.mapped('product_id.github_branch_id.repository_id')

        if not repos:
            _logger.info(
                'GITHUB ACCESS: No GitHub repos found for partner "%s" '
                'in mode order_lines. Access will be created without repos.',
                partner.display_name,
            )
        return repos
