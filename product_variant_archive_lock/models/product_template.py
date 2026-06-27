# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    variant_archive_lock = fields.Boolean(
        string="Keep manually archived variants",
        default=False,
        help="When enabled, variants that were archived by hand on this product "
             "are NOT reactivated automatically when the combinations are "
             "regenerated (after adding or changing attributes or values). "
             "Configure it per product.",
    )

    def _create_variant_ids(self):
        """Extiende la generación nativa de variantes.

        No se reimplementa nada de la lógica de Odoo: se delega en ``super()``
        (que crea/activa/archiva variantes según las combinaciones válidas) y,
        como post-proceso, se vuelven a archivar las variantes que el usuario
        había archivado manualmente en las plantillas con el candado activo.

        Esto es resiliente ante upgrades: solo depende del campo ``active`` y de
        nuestro propio campo ``manually_archived``, no de las internas del
        método nativo.
        """
        res = super()._create_variant_ids()

        locked_templates = self.filtered('variant_archive_lock')
        if not locked_templates:
            # Coste nulo para el caso general (sin opt-in).
            return res

        variants_to_rearchive = locked_templates.with_context(
            active_test=False,
        ).product_variant_ids.filtered(
            lambda v: v.active and v.manually_archived
        )
        if variants_to_rearchive:
            # action_archive es la ruta nativa: maneja la coherencia
            # plantilla<->variante (archiva la plantilla si se queda sin
            # variantes activas) y reafirma el marcado manual de forma
            # idempotente. No reentra en _create_variant_ids.
            variants_to_rearchive.action_archive()

        return res

    def _get_template_matrix(self, **kwargs):
        """Extend the order-grid matrix builder to hide flagged values.

        We do not reimplement the matrix logic: we just turn on the
        ``matrix_hide_values`` context flag and delegate to ``super()``. The
        flag propagates through the recordset chain, so every ``_only_active``
        call performed while building the matrix (columns, rows, report)
        filters out the values flagged ``hide_from_matrix`` -- and only those
        calls. Resilient against upgrades: it relies solely on the matrix
        reading its values via ``_only_active``.
        """
        return super(
            ProductTemplate, self.with_context(matrix_hide_values=True),
        )._get_template_matrix(**kwargs)
