
from odoo import models, api

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.depends('product_id', 'order_id.user_id', 'order_id.picking_type_id.warehouse_id', 'order_id.partner_id')
    def _compute_analytic_distribution(self):
        for line in self:
            # Smart Refresh: only compute if empty or product changed.
            # This respects manual user edits while providing warehouse defaults.
            product_changed = line._origin.product_id != line.product_id
            if not line.analytic_distribution or product_changed:
                super(PurchaseOrderLine, line)._compute_analytic_distribution()


    def _get_analytic_distribution_arguments(self, root_plans):
        res = super()._get_analytic_distribution_arguments(root_plans)
        res.update({
            'origin_warehouse_id': self.order_id.picking_type_id.warehouse_id.id,
            'dest_location_id': self.order_id.picking_type_id.default_location_dest_id.id,
            'user_id': self.order_id.user_id.id,
        })
        return res

