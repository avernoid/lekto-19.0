import random

from odoo import fields, models

# Simulated carrier statuses, in order: each update moves the delivery one step forward.
SIMULATED_STEPS = [
    ('recorded', 'Shipment recorded by the carrier'),
    ('in_transit', 'Shipment picked up by driver'),
    ('delivered', 'Delivered'),
]


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_simulation = fields.Boolean(
        string='Simulate Carrier Integration',
        help='For demos and training only: nothing is sent to the carrier. When a delivery is validated it '
             'gets a fictitious tracking number, and each status update moves it forward (recorded, in '
             'transit, delivered). Carrier integrations that support it (e.g. Sendcloud) simulate their '
             'own API instead. Never enable it in production.',
    )
    delivery_simulation_prefix = fields.Char(
        string='Simulated Tracking Prefix', default='SIM',
        help='Start of the fictitious tracking numbers, to make them look like the carrier ones '
             '(e.g. 1Z999AA1 for UPS).',
    )

    def _has_delivery_status_hook(self):
        """A carrier integration reports the delivery status by implementing
        ``<delivery_type>_get_delivery_state(picking)``, which returns a dict with
        ``code`` (technical code of stock.delivery.state), ``message`` (status in the
        carrier's words) and optionally ``data`` (JSON kept on the transfer).
        A carrier in simulation always has one."""
        return len(self) == 1 and (self._has_own_delivery_status_hook() or self.delivery_simulation)

    def _has_own_delivery_status_hook(self):
        return len(self) == 1 and bool(self.delivery_type) \
            and hasattr(self, '%s_get_delivery_state' % self.delivery_type)

    def _get_delivery_state(self, picking):
        self.ensure_one()
        if self._has_own_delivery_status_hook():
            return getattr(self, '%s_get_delivery_state' % self.delivery_type)(picking)
        if self.delivery_simulation:
            return self._simulate_delivery_state(picking)
        return {}

    def _simulate_delivery_state(self, picking):
        """Next simulated status of the delivery (stays delivered at the end)."""
        codes = [code for code, _message in SIMULATED_STEPS]
        current = picking.delivery_state_code
        index = codes.index(current) + 1 if current in codes else 0
        code, message = SIMULATED_STEPS[min(index, len(SIMULATED_STEPS) - 1)]
        return {'code': code, 'message': message, 'data': {'simulated': True}}

    def _simulate_tracking_number(self):
        self.ensure_one()
        return '%s%s' % (self.delivery_simulation_prefix or '', ''.join(random.choices('0123456789', k=10)))

    def send_shipping(self, pickings):
        res = super().send_shipping(pickings)
        if self._has_delivery_status_hook():
            pickings._set_delivery_state('recorded')
        return res

    def cancel_shipment(self, pickings):
        if self.delivery_simulation and not self._has_own_delivery_status_hook():
            # nothing to cancel at the carrier: only the state changes
            pickings._set_delivery_state('canceled', 'Shipment cancelled (simulation)')
            return
        res = super().cancel_shipment(pickings)
        if self._has_delivery_status_hook():
            pickings._set_delivery_state('canceled')
        return res
