from odoo import fields, models


class CarrierPurchaseCancel(models.TransientModel):
    _name = 'carrier.purchase.cancel'
    _description = 'Cancel Transport Purchase'

    picking_ids = fields.Many2many('stock.picking', string='Shipments', required=True)
    reason = fields.Char(
        string='Reason', required=True,
        help='Why the transport is not paid (e.g. shipment repeated, sent by another carrier). '
             'It is added to the description of the purchase line.')

    def action_confirm(self):
        self.ensure_one()
        self.picking_ids._cancel_carrier_purchase(self.reason)
        return {'type': 'ir.actions.act_window_close'}
