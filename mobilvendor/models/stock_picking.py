from odoo import fields, models

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    mobilvendor_route_id = fields.Many2one('mobilvendor.route', string='Logistics Route', index=True)