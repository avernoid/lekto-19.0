
from odoo import models, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('product_id', 'order_id.user_id', 'order_id.warehouse_id', 'order_id.partner_id')
    def _compute_analytic_distribution(self):
        for line in self:
            if not line.display_type:
                distribution = self.env['account.analytic.distribution.model']._get_distribution({
                    'product_id': line.product_id.id,
                    'product_categ_id': line.product_id.categ_id.id,
                    'partner_id': line.order_id.partner_id.id,
                    'partner_category_id': line.order_id.partner_id.category_id.ids,
                    'company_id': line.company_id.id,
                    'origin_warehouse_id': line.order_id.warehouse_id.id,
                    'origin_location_id': line.order_id.warehouse_id.lot_stock_id.id,
                    'invoice_user_id': line.order_id.user_id.id,
                    'user_id': line.order_id.user_id.id,
                })
                line.analytic_distribution = distribution or line.analytic_distribution
