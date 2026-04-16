
from odoo import models, api

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.depends('product_id', 'order_id.user_id', 'order_id.picking_type_id.warehouse_id', 'order_id.partner_id')
    def _compute_analytic_distribution(self):
        for line in self:
            if not line.display_type:
                distribution = self.env['account.analytic.distribution.model']._get_distribution({
                    'product_id': line.product_id.id,
                    'product_categ_id': line.product_id.categ_id.id,
                    'partner_id': line.order_id.partner_id.id,
                    'partner_category_id': line.order_id.partner_id.category_id.ids,
                    'company_id': line.company_id.id,
                    'origin_warehouse_id': line.order_id.picking_type_id.warehouse_id.id,
                    'dest_location_id': line.order_id.picking_type_id.default_location_dest_id.id,
                    'user_id': line.order_id.user_id.id,
                })
                line.analytic_distribution = distribution or line.analytic_distribution
