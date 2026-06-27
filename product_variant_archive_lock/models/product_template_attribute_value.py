# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ProductTemplateAttributeValue(models.Model):
    _inherit = 'product.template.attribute.value'

    hide_from_matrix = fields.Boolean(
        string="Hide from order grid",
        default=False,
        help="If enabled, this attribute value is not shown as a row or column "
             "in the Order Grid (sales matrix) of this product. The variants "
             "that use this value keep all their data, stock and history and "
             "remain active: they are only hidden from the grid, never "
             "archived, deleted or recreated by attribute changes, and the "
             "setting is kept even after you edit the product's attributes. "
             "Note: it only hides the value from the grid; the variant can "
             "still be sold through the product configurator or by selecting "
             "it directly.",
    )

    def _only_active(self):
        """Extend the active-values helper used to build the order grid.

        We do NOT change the meaning of ``ptav_active`` (that field still drives
        variant generation, exclusions, etc.). Instead, only when the matrix
        builder asks for the values through the ``matrix_hide_values`` context
        flag, we additionally drop the values flagged ``hide_from_matrix``.

        This keeps the feature display-only (variants are never archived) and
        confined to the grid: every other caller of ``_only_active`` is
        unaffected.
        """
        res = super()._only_active()
        if self.env.context.get('matrix_hide_values'):
            res = res.filtered(lambda ptav: not ptav.hide_from_matrix)
        return res
