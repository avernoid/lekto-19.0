import logging

from odoo import api, fields, models

from .stock_delivery_state import FINAL_CODES

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    delivery_state_id = fields.Many2one(
        'stock.delivery.state', string='Delivery State', tracking=True, copy=False, check_company=True,
        domain="[('company_id', '=', company_id)]",
        help='Where the delivery is. Set by the carrier integration, or by hand for carriers without one.')
    delivery_state_code = fields.Selection(
        related='delivery_state_id.code', store=True, string='Delivery State Code',
        help='Technical code of the delivery state, for filters and automations.')
    delivery_date_done = fields.Datetime(
        string='Delivery Date', tracking=True, copy=False,
        help='When the delivery reached a final state.')
    delivery_tracking_message = fields.Char(
        string='Carrier Status', readonly=True, copy=False,
        help='Last status reported by the carrier, in its own words.')
    delivery_tracking_history = fields.Text(
        string='Carrier Status History', readonly=True, copy=False,
        help='Every status reported by the carrier, with its date and time.')
    delivery_tracking_data = fields.Json(
        readonly=True, copy=False, help='Technical data of the last carrier status (parcel and status ids).')
    delivery_tracking_error = fields.Char(
        string='Carrier Status Error', readonly=True, copy=False,
        help='Error of the last automatic status request, if any.')
    delivery_status_auto = fields.Boolean(
        compute='_compute_delivery_status_auto',
        help='The carrier of the transfer reports the delivery state automatically.')

    @api.depends('carrier_id.delivery_type')
    def _compute_delivery_status_auto(self):
        for picking in self:
            picking.delivery_status_auto = picking.carrier_id._has_delivery_status_hook()

    def write(self, vals):
        res = super().write(vals)
        if vals.get('delivery_state_id'):
            self._on_delivery_state_change()
        return res

    def _on_delivery_state_change(self):
        for picking in self:
            state = picking.delivery_state_id
            if state.is_result_state and not picking.delivery_date_done:
                picking.delivery_date_done = fields.Datetime.now()
            if state.mail_template_id:
                picking.message_post_with_source(
                    state.mail_template_id, subtype_xmlid='mail.mt_comment',
                    email_layout_xmlid='mail.mail_notification_light')

    def _set_delivery_state(self, code, message=False, data=None):
        """Set the delivery state from a technical code (used by carrier integrations).

        ``message`` is the status in the carrier's words: it is kept as last status and
        appended to the history when it changes. Unknown codes leave the state as it is."""
        for picking in self:
            vals = {'delivery_tracking_error': False}
            if data is not None:
                vals['delivery_tracking_data'] = data
            if message and message != picking.delivery_tracking_message:
                line = '%s %s' % (fields.Datetime.to_string(fields.Datetime.now()), message)
                vals['delivery_tracking_message'] = message
                vals['delivery_tracking_history'] = '\n'.join(filter(None, [picking.delivery_tracking_history, line]))
            state = self.env['stock.delivery.state']._get_by_code(code, picking.company_id)
            if state and state != picking.delivery_state_id:
                vals['delivery_state_id'] = state.id
            picking.write(vals)

    def action_update_delivery_state(self):
        """Ask the carrier for the current status of these transfers (or simulate it)."""
        for picking in self.filtered('delivery_status_auto'):
            result = picking.carrier_id._get_delivery_state(picking) or {}
            picking._set_delivery_state(result.get('code'), result.get('message'), result.get('data'))
        return True

    def _action_done(self):
        res = super()._action_done()
        self._simulate_carrier_shipment()
        return res

    def _simulate_carrier_shipment(self):
        """Simulated carriers without own integration: a fictitious tracking number and the
        'recorded' state when a delivery to a customer is validated."""
        for picking in self.filtered(lambda p: p.state == 'done' and p.carrier_id.delivery_simulation
                                     and not p.carrier_id._has_own_delivery_status_hook()
                                     and p.location_dest_id.usage == 'customer'):
            if not picking.carrier_tracking_ref:
                picking.carrier_tracking_ref = picking.carrier_id._simulate_tracking_number()
            if not picking.delivery_state_id:
                picking._set_delivery_state('recorded', 'Shipment recorded by the carrier (simulation)',
                                            {'simulated': True})

    @api.model
    def _cron_update_delivery_state(self, limit=500):
        """Scheduled action: ask the carriers about the transfers still on their way."""
        pickings = self.search([
            ('state', '=', 'done'),
            ('delivery_state_id', '!=', False),
            ('delivery_state_code', 'not in', FINAL_CODES),
            ('carrier_id', '!=', False),
        ], order='delivery_date_done desc, id', limit=limit)
        for picking in pickings.filtered('delivery_status_auto'):
            try:
                with self.env.cr.savepoint():
                    picking.action_update_delivery_state()
            except Exception as error:  # noqa: BLE001 - one carrier error must not stop the others
                _logger.warning('Delivery status of %s not updated: %s', picking.name, error)
                picking.delivery_tracking_error = str(error)[:250]
