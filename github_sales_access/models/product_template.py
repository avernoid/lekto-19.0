import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)

_REPOS_DEFAULT_MODE = [
    ('list', 'Lista fija de repositorios'),
    ('order_lines', 'Basado en módulos comprados por el cliente'),
]


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_github_connector = fields.Boolean(
        string='Es GitHub Connector',
        default=False,
        help='Marca este producto como "GitHub Connector". '
             'Al estar activo, aparecerá el Smart Button de accesos GitHub '
             'en los pedidos de venta que incluyan este producto.',
    )
    repos_default_mode = fields.Selection(
        selection=_REPOS_DEFAULT_MODE,
        string='Repos por defecto',
        default='list',
        help=(
            'Define cómo se determina el listado de repositorios cuando se crea '
            'un acceso GitHub automáticamente:\n\n'
            '• Lista fija: usa los repositorios indicados en "Repositorios Incluidos".\n'
            '• Basado en módulos comprados: busca en todos los pedidos confirmados '
            '  del cliente (incluyendo el pedido actual) los productos que tienen '
            '  una rama GitHub vinculada y extrae su repositorio.'
        ),
    )
    github_repository_ids = fields.Many2many(
        comodel_name='github.repository',
        relation='product_template_github_repository_rel',
        column1='product_template_id',
        column2='repository_id',
        string='Repositorios Incluidos',
        help='Repositorios de GitHub a los que da acceso este producto. '
             'Solo se usa cuando "Repos por defecto" = "Lista fija".',
    )

    # ── Helper ──────────────────────────────────────────────────────────────────

    def get_github_repos_for_partner(self, partner, current_order=None):
        """Devuelve los github.repository que corresponden a este conector
        para un cliente dado, según el modo configurado.

        :param partner: res.partner — el cliente del pedido
        :param current_order: sale.order — el pedido actual (incluido aunque
               no esté confirmado aún, para cubrir el momento de confirmación)
        :return: recordset de github.repository sin duplicados
        """
        self.ensure_one()

        if self.repos_default_mode == 'list':
            return self.github_repository_ids

        # ── Modo order_lines ─────────────────────────────────────────────────
        # 1. Buscar en todos los pedidos confirmados del cliente
        domain = [
            ('order_id.partner_id', '=', partner.id),
            ('order_id.state', '=', 'sale'),
            ('product_id.github_branch_id', '!=', False),
        ]
        lines = self.env['sale.order.line'].search(domain)

        # 2. Añadir líneas del pedido actual (puede no estar en state='sale' aún)
        if current_order:
            current_lines = current_order.order_line.filtered(
                lambda l: l.product_id.github_branch_id
            )
            # El operador | sobre recordsets ya deduplica automáticamente
            lines |= current_lines

        # 3. Extraer repos — mapped() garantiza recordset sin duplicados
        repos = lines.mapped('product_id.github_branch_id.repository_id')

        if not repos:
            _logger.info(
                'GITHUB ACCESS: No GitHub repos found for partner "%s" '
                'in mode order_lines. Access record will be created without repo lines.',
                partner.display_name,
            )
        return repos
