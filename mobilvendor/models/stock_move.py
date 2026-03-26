from odoo import fields, models

class StockMove(models.Model):
    _inherit = 'stock.move'

    mobilvendor_id = fields.Char(
        string="Mobilvendor ID",
        help="ID of the transfer from the external system",
        index=True
    )
    mobilvendor_route_id = fields.Many2one(
        'mobilvendor.route',
        string='Route',
        related='picking_id.mobilvendor_route_id',
        store=True,
        readonly=True
    )