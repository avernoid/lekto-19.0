from odoo import fields, models

from .sendcloud_service import SendCloudDropship, SendCloudSimulation

# Sendcloud parcel status id (GET /parcels/statuses) -> technical code of stock.delivery.state
# (delivery_status_tracking). Statuses not listed (1337 "Unknown status", or new ones) leave
# the delivery state as it is.
SENDCLOUD_DELIVERY_STATES = {
    'recorded': {999, 1001, 1000, 1, 13},
    'in_transit': {22, 3, 5, 6, 7, 62990, 62989, 91, 92, 4, 62993, 62994, 62995, 12},
    'delivered': {11, 93},
    'incident': {8, 80, 62991, 62992, 62996, 62997, 1002, 15, 94},
    'canceled': {2001, 1999, 1998, 2000},
}


def sendcloud_delivery_state_code(status_id):
    return next((code for code, ids in SENDCLOUD_DELIVERY_STATES.items() if status_id in ids), False)


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    sendcloud_contract_id = fields.Integer(
        string='Sendcloud Contract ID',
        help='Id of the carrier contract in Sendcloud (Shipping > Carriers > My contracts) to use for '
             'every parcel of this method. Leave empty to let Sendcloud use the default contract of '
             'the carrier.',
    )
    sendcloud_sender_from_odoo = fields.Boolean(
        string='Sender Address from Odoo',
        help='Send the warehouse address from Odoo as sender instead of looking for a Sendcloud '
             'sender address named like the warehouse. Dropships always use the vendor address.',
    )

    def _get_sendcloud(self):
        if self.delivery_simulation:
            return SendCloudSimulation(self.sudo().sendcloud_public_key, self.sudo().sendcloud_secret_key,
                                       self.log_xml, self)
        return SendCloudDropship(self.sudo().sendcloud_public_key, self.sudo().sendcloud_secret_key, self.log_xml)

    def sendcloud_get_tracking_link(self, picking):
        if self.delivery_simulation:
            # no Sendcloud tracking page in simulation: the carrier page of the method, if any
            if self.tracking_url and picking.carrier_tracking_ref:
                return self.tracking_url.replace('<shipmenttrackingnumber>', picking.carrier_tracking_ref)
            return False
        return super().sendcloud_get_tracking_link(picking)

    def _sendcloud_simulated_status(self, picking):
        """Next Sendcloud parcel status in simulation: ready to send, picked up, delivered."""
        steps = [(1000, 'Ready to send'), (22, 'Shipment picked up by driver'), (11, 'Delivered')]
        codes = [sendcloud_delivery_state_code(status_id) for status_id, _message in steps]
        current = picking.delivery_state_code
        index = codes.index(current) + 1 if current in codes else 0
        return steps[min(index, len(steps) - 1)]

    def sendcloud_get_delivery_state(self, picking):
        """Hook of delivery_status_tracking: status of the (first) parcel of the transfer."""
        self.ensure_one()
        refs = picking.sendcloud_parcel_ref or []
        if not refs:
            return {}
        parcel_id = refs[0][0] if isinstance(refs[0], list) else refs[0]
        if self.delivery_simulation:
            status_id, message = self._sendcloud_simulated_status(picking)
            status = {'id': status_id, 'message': message}
        else:
            parcel = self._get_sendcloud()._track_shipment(parcel_id)
            status = parcel.get('status') or {}
        return {
            'code': sendcloud_delivery_state_code(status.get('id')),
            'message': status.get('message'),
            'data': {'parcel_id': parcel_id, 'status_id': status.get('id'), 'status': status.get('message')},
        }
