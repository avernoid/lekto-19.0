from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    dependency_parent_name = fields.Char(
        string='Required by (Module)',
        compute='_compute_dependency_parent_name',
        help='Name of the parent module that requires this product '
             'as a dependency. Empty if this line is not a dependency.',
    )

    @api.depends(
        'product_id',
        'order_id.order_line.product_id',
    )
    def _compute_dependency_parent_name(self):
        for line in self:
            parent_name = ''
            line_tmpl = line.product_id.product_tmpl_id
            if line_tmpl and line_tmpl.is_odoo_module:
                for other_line in line.order_id.order_line:
                    other_tmpl = other_line.product_id.product_tmpl_id
                    if (
                        other_tmpl != line_tmpl
                        and other_tmpl.is_odoo_module
                        and line_tmpl in other_tmpl.all_dependency_ids
                    ):
                        parent_name = other_tmpl.name
                        break
            line.dependency_parent_name = parent_name
