from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_odoo_module = fields.Boolean(
        string='Is Odoo Module',
        default=False,
        help='Mark this product as an Odoo module to enable dependency '
             'management. When enabled, you can link other module products '
             'as dependencies. The eCommerce will auto-add missing '
             'dependencies to the cart and display the total price '
             'including all required modules.',
    )
    technical_module_name = fields.Char(
        string='Technical Module Name',
        help='Technical name of the Odoo module, e.g. "github_connector_api". '
             'Used for automatic dependency suggestion from module manifests.',
    )
    dependency_ids = fields.Many2many(
        comodel_name='product.template',
        relation='product_template_dependency_rel',
        column1='product_id',
        column2='dependency_id',
        string='Module Dependencies',
        help='Other module products that this module depends upon. '
             'When a customer adds this module to their cart, all '
             'dependencies will be automatically added as separate '
             'cart lines. Dependencies are resolved recursively.',
    )
    all_dependency_ids = fields.Many2many(
        comodel_name='product.template',
        relation='product_template_all_dependency_rel',
        column1='product_id',
        column2='dependency_id',
        string='All Dependencies (cached)',
        compute='_compute_all_dependency_ids',
        store=True,
        help='Flattened list of all recursive dependencies. '
             'Stored for performance — avoids recursive traversal '
             'on every page render.',
    )
    total_price_with_deps = fields.Float(
        string='Total Price (with Dependencies)',
        compute='_compute_total_price_with_deps',
        help='The total price of this module including all its '
             'recursive dependencies. Duplicate dependencies are '
             'counted only once.',
    )
    dependency_count = fields.Integer(
        string='Dependency Count',
        compute='_compute_total_price_with_deps',
        help='Total number of unique recursive dependencies.',
    )
    published_dependency_ids = fields.Many2many(
        comodel_name='product.template',
        compute='_compute_published_dependencies',
        string='Published Dependencies',
        help='Only dependencies that are published on the website.',
    )
    published_dependency_count = fields.Integer(
        string='Published Dependency Count',
        compute='_compute_published_dependencies',
        help='Number of published recursive dependencies.',
    )

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('dependency_ids')
    def _check_no_circular_dependency(self):
        """Prevent circular dependency chains.

        Raises ValidationError if adding a dependency would create a
        cycle (e.g. A→B→C→A or A→A).
        """
        for product in self:
            if not product.dependency_ids:
                continue
            if product._has_circular_dependency():
                raise ValidationError(
                    "Circular dependency detected: '%(name)s' appears in "
                    "its own dependency chain. Please review the "
                    "dependency configuration."
                    % {'name': product.display_name}
                )

    def _has_circular_dependency(self):
        """Check if this product appears in its own dependency chain.

        Uses iterative BFS starting from direct dependencies, checking
        if self is reachable.  Does NOT add self to visited initially,
        so both direct self-references and indirect cycles are detected.

        :return: True if a cycle is detected
        :rtype: bool
        """
        self.ensure_one()
        visited = set()
        stack = list(self.dependency_ids.ids)
        while stack:
            dep_id = stack.pop()
            if dep_id == self.id:
                return True
            if dep_id in visited:
                continue
            visited.add(dep_id)
            dep = self.browse(dep_id)
            stack.extend(dep.dependency_ids.ids)
        return False

    # ------------------------------------------------------------------
    # Computed fields
    # ------------------------------------------------------------------
    @api.depends('dependency_ids', 'dependency_ids.dependency_ids')
    def _compute_all_dependency_ids(self):
        """Flatten the recursive dependency tree into a stored M2M."""
        for product in self:
            if product.is_odoo_module and product.dependency_ids:
                product.all_dependency_ids = product._get_all_dependencies()
            else:
                product.all_dependency_ids = False

    @api.depends('list_price', 'all_dependency_ids', 'all_dependency_ids.list_price')
    def _compute_total_price_with_deps(self):
        for product in self:
            if product.is_odoo_module and product.all_dependency_ids:
                product.total_price_with_deps = (
                    product.list_price
                    + sum(product.all_dependency_ids.mapped('list_price'))
                )
                product.dependency_count = len(product.all_dependency_ids)
            else:
                product.total_price_with_deps = product.list_price
                product.dependency_count = 0

    @api.depends('all_dependency_ids', 'all_dependency_ids.website_published')
    def _compute_published_dependencies(self):
        """Filter all_dependency_ids to only published products."""
        for product in self:
            published = product.all_dependency_ids.filtered('website_published')
            product.published_dependency_ids = published
            product.published_dependency_count = len(published)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_all_dependencies(self, visited=None):
        """Return all recursive dependencies as a recordset, avoiding cycles.

        :param set visited: set of product.template IDs already visited
        :return: recordset of all unique dependency product.template records
        :rtype: recordset
        """
        self.ensure_one()
        if visited is None:
            visited = set()
        visited.add(self.id)

        all_deps = self.env['product.template']
        for dep in self.dependency_ids:
            if dep.id in visited:
                continue
            all_deps |= dep
            all_deps |= dep._get_all_dependencies(visited=visited)
        return all_deps
