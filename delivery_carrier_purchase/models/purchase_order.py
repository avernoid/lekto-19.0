from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    carrier_purchase_period = fields.Char(
        string='Transport Period', readonly=True, copy=False, index='btree_not_null',
        help='Set on the purchases of transport created from shipments: the period (month, week, '
             'day) whose shipments this request for quotation gathers.')
    carrier_picking_count = fields.Integer(
        string='Shipments', compute='_compute_carrier_picking_count',
        help='Shipments whose transport is bought in this purchase.')

    @api.depends('order_line.carrier_picking_ids')
    def _compute_carrier_picking_count(self):
        for order in self:
            order.carrier_picking_count = len(order.order_line.carrier_picking_ids)

    def action_view_carrier_pickings(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('stock.action_picking_tree_all')
        action['domain'] = [('id', 'in', self.order_line.carrier_picking_ids.ids)]
        action['context'] = {'create': False}
        return action


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    carrier_picking_ids = fields.One2many(
        'stock.picking', 'carrier_purchase_line_id', string='Shipments',
        help='Shipments whose transport is bought with this line.')
