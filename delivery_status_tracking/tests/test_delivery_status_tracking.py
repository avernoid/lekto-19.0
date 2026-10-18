from contextlib import contextmanager
from unittest.mock import patch

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestDeliveryStatusTracking(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)
        cls.customer = cls.env['res.partner'].create({'name': 'Customer', 'email': 'customer@example.com'})
        cls.product = cls.env['product.product'].create({'name': 'Cups', 'type': 'consu', 'weight': 1.0})
        cls.carrier = cls.env['delivery.carrier'].create({
            'name': 'Carrier with API', 'delivery_type': 'fixed', 'fixed_price': 5.0,
            'product_id': cls.env['product.product'].create({'name': 'Shipping', 'type': 'service'}).id,
        })
        cls.warehouse.out_type_id.print_label = True
        cls.State = cls.env['stock.delivery.state']

    def setUp(self):
        super().setUp()
        self.carrier_status = {'code': 'in_transit', 'message': 'Picked up'}

    @contextmanager
    def _carrier_api(self, fail_for=None):
        """Give the fixed carrier a delivery status hook, as a real integration would."""
        test = self

        def get_delivery_state(carrier, picking):
            if fail_for and picking in fail_for:
                raise ValueError('carrier API down')
            return dict(test.carrier_status, data={'picking': picking.name})

        model = type(self.env['delivery.carrier'])
        with patch.object(model, 'fixed_get_delivery_state', get_delivery_state, create=True), \
                patch.object(model, 'fixed_cancel_shipment', lambda carrier, pickings: None):
            yield

    def _delivery(self, carrier=None):
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.out_type_id.id,
            'partner_id': self.customer.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'carrier_id': carrier and carrier.id,
            'move_ids': [(0, 0, {
                'name': 'Cups', 'product_id': self.product.id, 'product_uom_qty': 2,
                'location_id': self.warehouse.lot_stock_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            })],
        })
        picking.action_confirm()
        return picking

    def _validate(self, picking):
        picking.move_ids.quantity = 2
        picking.move_ids.picked = True
        picking.with_context(skip_sms=True).button_validate()
        self.assertEqual(picking.state, 'done')

    def test_default_states(self):
        codes = self.State.search([('company_id', '=', self.env.company.id)]).mapped('code')
        for code in ('recorded', 'in_transit', 'delivered', 'incident', 'canceled'):
            self.assertIn(code, codes)
        delivered = self.State._get_by_code('delivered', self.env.company)
        self.assertTrue(delivered.is_result_state)
        self.assertEqual(delivered.result_type, 'success')

    def test_validation_with_integrated_carrier_records_the_shipment(self):
        picking = self._delivery(self.carrier)
        with self._carrier_api():
            self.assertTrue(picking.delivery_status_auto)
            self._validate(picking)
        self.assertEqual(picking.delivery_state_code, 'recorded')
        self.assertFalse(picking.delivery_date_done)

    def test_carrier_without_hook_sets_nothing(self):
        picking = self._delivery(self.carrier)
        self.assertFalse(picking.delivery_status_auto)
        self._validate(picking)
        self.assertFalse(picking.delivery_state_id)

    def test_update_from_carrier_and_history(self):
        picking = self._delivery(self.carrier)
        with self._carrier_api():
            self._validate(picking)
            picking.action_update_delivery_state()
            self.assertEqual(picking.delivery_state_code, 'in_transit')
            self.assertEqual(picking.delivery_tracking_message, 'Picked up')
            self.assertEqual(picking.delivery_tracking_data, {'picking': picking.name})
            # unknown status: the state stays, the message is recorded
            self.carrier_status = {'code': False, 'message': 'Unknown status'}
            picking.action_update_delivery_state()
            self.assertEqual(picking.delivery_state_code, 'in_transit')
            self.carrier_status = {'code': 'delivered', 'message': 'Delivered'}
            picking.action_update_delivery_state()
        self.assertEqual(picking.delivery_state_code, 'delivered')
        self.assertTrue(picking.delivery_date_done)
        self.assertEqual(len(picking.delivery_tracking_history.splitlines()), 3)

    def test_cron_skips_final_and_survives_errors(self):
        ok, broken, delivered = (self._delivery(self.carrier) for _ in range(3))
        with self._carrier_api(fail_for=broken):
            for picking in (ok, broken, delivered):
                self._validate(picking)
            delivered._set_delivery_state('delivered')
            self.carrier_status = {'code': 'incident', 'message': 'Address invalid'}
            with self.assertLogs('odoo.addons.delivery_status_tracking.models.stock_picking', 'WARNING') as logs:
                self.env['stock.picking']._cron_update_delivery_state()
        self.assertEqual(len(logs.output), 1)
        self.assertIn(broken.name, logs.output[0])
        self.assertEqual(ok.delivery_state_code, 'incident')
        self.assertEqual(broken.delivery_state_code, 'recorded')
        self.assertIn('carrier API down', broken.delivery_tracking_error)
        self.assertEqual(delivered.delivery_state_code, 'delivered', 'final states are not asked again')

    def test_cancel_shipment(self):
        picking = self._delivery(self.carrier)
        with self._carrier_api():
            self._validate(picking)
            picking.cancel_shipment()
        self.assertEqual(picking.delivery_state_code, 'canceled')

    def test_manual_state_without_carrier(self):
        picking = self._delivery()
        self._validate(picking)
        picking.delivery_state_id = self.State._get_by_code('delivered', self.env.company)
        self.assertTrue(picking.delivery_date_done)

    def test_mail_template_on_state(self):
        template = self.env['mail.template'].create({
            'name': 'Delivered', 'model_id': self.env.ref('stock.model_stock_picking').id,
            'subject': 'Your order {{ object.name }} was delivered', 'body_html': '<p>Delivered</p>',
        })
        self.State._get_by_code('delivered', self.env.company).mail_template_id = template
        picking = self._delivery()
        self._validate(picking)
        picking._set_delivery_state('delivered')
        self.assertTrue(picking.message_ids.filtered(lambda m: m.subject == 'Your order %s was delivered' % picking.name))

    def test_other_company_gets_its_own_states(self):
        company = self.env['res.company'].create({'name': 'Second Company'})
        state = self.State._get_by_code('in_transit', company)
        self.assertEqual(state.company_id, company)
        self.assertEqual(state.code, 'in_transit')
        self.assertEqual(self.State._get_by_code('in_transit', company), state, 'copied only once')

    def test_simulation_full_flow(self):
        self.carrier.write({'delivery_simulation': True, 'delivery_simulation_prefix': '1Z999AA1'})
        picking = self._delivery(self.carrier)
        self.assertTrue(picking.delivery_status_auto)
        self._validate(picking)
        self.assertTrue(picking.carrier_tracking_ref.startswith('1Z999AA1'))
        self.assertEqual(len(picking.carrier_tracking_ref), len('1Z999AA1') + 10)
        self.assertEqual(picking.delivery_state_code, 'recorded')
        picking.action_update_delivery_state()
        self.assertEqual(picking.delivery_state_code, 'in_transit')
        picking.action_update_delivery_state()
        self.assertEqual(picking.delivery_state_code, 'delivered')
        self.assertTrue(picking.delivery_date_done)
        picking.action_update_delivery_state()
        self.assertEqual(picking.delivery_state_code, 'delivered', 'stays delivered')
        self.assertTrue(picking.delivery_tracking_data.get('simulated'))

    def test_simulation_cron_and_cancel(self):
        self.carrier.delivery_simulation = True
        moving, cancelled = self._delivery(self.carrier), self._delivery(self.carrier)
        self._validate(moving)
        self._validate(cancelled)
        cancelled.cancel_shipment()
        self.assertEqual(cancelled.delivery_state_code, 'canceled')
        self.env['stock.picking']._cron_update_delivery_state()
        self.assertEqual(moving.delivery_state_code, 'in_transit')
        self.assertEqual(cancelled.delivery_state_code, 'canceled', 'cancelled deliveries are not asked again')

    def test_simulation_keeps_typed_tracking_number(self):
        self.carrier.delivery_simulation = True
        picking = self._delivery(self.carrier)
        picking.carrier_tracking_ref = 'TYPED123'
        self._validate(picking)
        self.assertEqual(picking.carrier_tracking_ref, 'TYPED123')
        self.assertEqual(picking.delivery_state_code, 'recorded')

    def test_demo_deliveries_ready_to_validate(self):
        picking = self.env.ref('delivery_status_tracking.picking_out_hotel_ups', raise_if_not_found=False)
        if not picking:
            self.skipTest('installed without demo data')
        self.assertTrue(picking.carrier_id.delivery_simulation)
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
        picking.move_ids.picked = True
        picking.with_context(skip_sms=True).button_validate()
        self.assertTrue(picking.carrier_tracking_ref.startswith('1Z999AA1'))
        self.assertIn('ups.com/track', picking.carrier_tracking_url)
        self.assertEqual(picking.delivery_state_code, 'recorded')
