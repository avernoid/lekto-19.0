from contextlib import contextmanager
from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from odoo.addons.delivery_sendcloud.models.sendcloud_service import SendCloud

PARCEL_ID = 501
TRACKING = '1ZTESTDROPSHIP'


@tagged('post_install', '-at_install')
class TestSendcloudDropship(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.es = cls.env.ref('base.es')
        cls.company_partner = cls.env.company.partner_id
        cls.company_partner.write({
            'street': 'Can Diners 1', 'city': 'Argentona', 'zip': '08310', 'country_id': cls.es.id,
            'phone': '+34 937000000', 'email': 'shipping@company.example.com',
        })
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Vendor Printing', 'is_company': True, 'street': 'C/ Moianes 9',
            'city': 'Sant Quirze del Valles', 'zip': '08192', 'country_id': cls.es.id,
            'phone': '+34 930000000', 'email': 'vendor@example.com',
        })
        cls.customer = cls.env['res.partner'].create({
            'name': 'Customer Co', 'is_company': True, 'email': 'orders@customer.example.com',
            'phone': '+33 300000000',
        })
        # delivery address without email nor phone: they must come from the customer company
        cls.delivery_address = cls.env['res.partner'].create({
            'type': 'delivery', 'parent_id': cls.customer.id, 'name': 'Reception',
            'street': '40 Place Paul Asseman', 'city': 'Dunkerque', 'zip': '59140',
            'country_id': cls.env.ref('base.fr').id,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Napkins', 'is_storable': True, 'weight': 0.5,
            'route_ids': [(6, 0, cls.env.ref('stock_dropshipping.route_drop_shipping').ids)],
            'seller_ids': [(0, 0, {'partner_id': cls.vendor.id, 'price': 1.0})],
        })
        cls.consumable = cls.env['product.product'].create({'name': 'Cups', 'type': 'consu', 'weight': 1.0})
        sendcloud_product = cls.env['sendcloud.shipping.product'].create({
            'name': 'UPS Standard', 'sendcloud_code': 'ups:standard', 'carrier': 'ups',
            'min_weight': 1, 'max_weight': 70001,
            'functionalities': {'bool_func': [], 'detail_func': {}, 'customizable': {}},
        })
        cls.carrier = cls.env['delivery.carrier'].create({
            'name': 'Sendcloud UPS', 'delivery_type': 'sendcloud', 'prod_environment': True,
            'product_id': cls.env['product.product'].create({'name': 'Shipping', 'type': 'service'}).id,
            'sendcloud_public_key': 'mock', 'sendcloud_secret_key': 'mock', 'country_id': cls.es.id,
            'sendcloud_contract_id': 239243,
        })
        # computed from the country (reset on create): set it afterwards, as _set_sendcloud_products does
        cls.carrier.sendcloud_shipping_id = sendcloud_product
        cls.warehouse.out_type_id.print_label = True

    def setUp(self):
        super().setUp()
        self.requests = []
        self.parcel_status = {'id': 1000, 'message': 'Ready to send'}

    @contextmanager
    def _mock_sendcloud(self):
        test = self

        def _send_request(service, endpoint, method='get', data=None, params=None, route=None):
            test.requests.append((method, endpoint, data, params))
            if endpoint == 'shipping-products':
                return [{
                    'code': 'ups:standard', 'carrier': 'ups', 'name': 'UPS Standard',
                    'weight_range': {'min_weight': 1, 'max_weight': 70001},
                    'methods': [{'id': 5606, 'name': 'UPS Standard', 'functionalities': {},
                                 'properties': {'min_weight': 1, 'max_weight': 70001}}],
                }]
            if endpoint == 'shipping-functionalities':
                return {}
            if endpoint == 'shipping-price':
                return [{'price': '7.5', 'currency': test.env.company.currency_id.name}]
            if endpoint == 'user/addresses/sender':
                return {'sender_addresses': [{'id': 77, 'label': test.warehouse.name, 'contact_name': ''}]}
            if endpoint == 'parcels' and method == 'post':
                return {'parcels': [{
                    'id': PARCEL_ID, 'tracking_number': TRACKING, 'tracking_url': 'https://track',
                    'colli_uuid': 'colli-1', 'weight': '5.000', 'shipment': {'id': 5606},
                    'documents': [{'link': '/label', 'type': 'label'}],
                }]}
            if endpoint == f'parcels/{PARCEL_ID}' and method == 'get':
                return {'parcel': {'id': PARCEL_ID, 'tracking_url': 'https://track', 'status': test.parcel_status}}
            if endpoint == f'parcels/{PARCEL_ID}/cancel':
                return {'status': 'queued'}
            raise AssertionError('Unexpected Sendcloud call %s %s' % (method, endpoint))

        with patch.object(SendCloud, '_send_request', autospec=True, side_effect=_send_request), \
                patch.object(SendCloud, '_get_document', autospec=True, return_value=b'%PDF-label'):
            yield

    def _posted_parcel(self):
        posted = [r for r in self.requests if r[0] == 'post' and r[1] == 'parcels']
        self.assertEqual(len(posted), 1, 'exactly one parcel creation expected')
        return posted[0][2]['parcels'][0]

    def _validate(self, picking):
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
        picking.move_ids.picked = True
        picking.with_context(skip_sms=True, skip_backorder=True).button_validate()
        self.assertEqual(picking.state, 'done')

    def _dropship(self):
        order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'partner_shipping_id': self.delivery_address.id,
            'order_line': [(0, 0, {'product_id': self.product.id, 'product_uom_qty': 10})],
        })
        order.action_confirm()
        purchase = order._get_purchase_orders()
        purchase.button_confirm()
        picking = purchase.picking_ids
        picking.picking_type_id.print_label = True
        picking.carrier_id = self.carrier
        return picking

    def _outgoing(self):
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.out_type_id.id,
            'partner_id': self.delivery_address.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'carrier_id': self.carrier.id,
            'move_ids': [(0, 0, {
                'name': 'Cups', 'product_id': self.consumable.id, 'product_uom_qty': 3,
                'location_id': self.warehouse.lot_stock_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            })],
        })
        picking.action_confirm()
        return picking

    def test_dropship_parcel_from_vendor_to_customer(self):
        picking = self._dropship()
        self.assertEqual(picking.partner_id, self.vendor)
        with self._mock_sendcloud():
            self._validate(picking)
        parcel = self._posted_parcel()
        # recipient: the purchase delivery address, not the vendor
        self.assertEqual(parcel['city'], 'Dunkerque')
        self.assertEqual(parcel['postal_code'], '59140')
        self.assertEqual(parcel['country'], 'FR')
        # email and phone come from the customer company (UPS requires the email)
        self.assertEqual(parcel['email'], 'orders@customer.example.com')
        self.assertEqual(parcel['telephone'], '+33 300000000')
        # sender: the vendor, as from_* fields and without a Sendcloud sender address
        self.assertNotIn('sender_address', parcel)
        self.assertEqual(parcel['from_city'], 'Sant Quirze del Valles')
        self.assertEqual(parcel['from_country'], 'ES')
        self.assertEqual(parcel['from_email'], 'vendor@example.com')
        self.assertEqual(parcel['contract'], 239243)
        self.assertEqual(parcel['order_number'], picking.sale_id.name)
        # result on the transfer
        self.assertEqual(picking.carrier_tracking_ref, TRACKING)
        self.assertEqual(picking.sendcloud_parcel_ref, [[PARCEL_ID]])
        self.assertEqual(picking.delivery_state_code, 'recorded')
        self.assertEqual(picking.carrier_price, 7.5, 'the rate must be computed with the vendor country')
        self.assertFalse(picking.message_ids.filtered(lambda m: 'Failed to get the actual price' in (m.body or '')))
        # the transfer itself is untouched
        self.assertEqual(picking.partner_id, self.vendor)

    def test_dropship_sender_without_contact_data_uses_company(self):
        self.vendor.write({'email': False, 'phone': False})
        picking = self._dropship()
        with self._mock_sendcloud():
            self._validate(picking)
        parcel = self._posted_parcel()
        self.assertEqual(parcel['from_city'], 'Sant Quirze del Valles')
        self.assertEqual(parcel['from_email'], 'shipping@company.example.com')
        self.assertEqual(parcel['from_telephone'], '+34 937000000')

    def test_outgoing_uses_sendcloud_sender_address(self):
        picking = self._outgoing()
        with self._mock_sendcloud():
            self._validate(picking)
        parcel = self._posted_parcel()
        self.assertEqual(parcel['sender_address'], 77)
        self.assertNotIn('from_city', parcel)
        self.assertEqual(parcel['city'], 'Dunkerque')
        self.assertEqual(parcel['email'], 'orders@customer.example.com')

    def test_outgoing_sender_from_odoo(self):
        self.carrier.sendcloud_sender_from_odoo = True
        picking = self._outgoing()
        with self._mock_sendcloud():
            self._validate(picking)
        parcel = self._posted_parcel()
        self.assertNotIn('sender_address', parcel)
        self.assertEqual(parcel['from_city'], 'Argentona')
        self.assertFalse([r for r in self.requests if r[1] == 'user/addresses/sender'])

    def test_no_contract_configured(self):
        self.carrier.sendcloud_contract_id = 0
        picking = self._dropship()
        with self._mock_sendcloud():
            self._validate(picking)
        self.assertNotIn('contract', self._posted_parcel())

    def test_delivery_state_from_parcel_status(self):
        picking = self._dropship()
        with self._mock_sendcloud():
            self._validate(picking)
            for status_id, message, expected in [
                (1337, 'Unknown status', 'recorded'),
                (22, 'Shipment picked up by driver', 'in_transit'),
                (8, 'Delivery attempt failed', 'incident'),
                (11, 'Delivered', 'delivered'),
            ]:
                self.parcel_status = {'id': status_id, 'message': message}
                picking.action_update_delivery_state()
                self.assertEqual(picking.delivery_state_code, expected, message)
                self.assertEqual(picking.delivery_tracking_message, message)
        self.assertTrue(picking.delivery_date_done)
        self.assertEqual(picking.delivery_tracking_data['status_id'], 11)
        self.assertEqual(len(picking.delivery_tracking_history.splitlines()), 4)

    def test_delivery_state_cron_picks_sendcloud_transfers(self):
        picking = self._dropship()
        with self._mock_sendcloud():
            self._validate(picking)
            self.parcel_status = {'id': 22, 'message': 'Shipment picked up by driver'}
            self.env['stock.picking']._cron_update_delivery_state()
        self.assertEqual(picking.delivery_state_code, 'in_transit')

    def test_delivery_state_cancel(self):
        picking = self._dropship()
        with self._mock_sendcloud():
            self._validate(picking)
            picking.cancel_shipment()
        self.assertEqual(picking.delivery_state_code, 'canceled')

    @contextmanager
    def _no_network(self):
        def forbidden(*args, **kwargs):
            raise AssertionError('the simulation must not call Sendcloud')
        with patch('requests.Session.request', forbidden):
            yield

    def test_simulation_full_flow_without_network(self):
        self.carrier.write({'delivery_simulation': True, 'delivery_simulation_prefix': '1Z999AA1'})
        picking = self._dropship()
        with self._no_network():
            self._validate(picking)
            self.assertTrue(picking.carrier_tracking_ref.startswith('1Z999AA1'))
            self.assertTrue(picking.sendcloud_parcel_ref)
            self.assertEqual(picking.delivery_state_code, 'recorded')
            self.assertGreater(picking.carrier_price, 0, 'simulated rate (EUR, converted to the company currency)')
            label = self.env['ir.attachment'].search([('res_model', '=', 'stock.picking'), ('res_id', '=', picking.id)])
            self.assertTrue(label, 'the simulated label is attached to the transfer')
            # a readable label: carrier, vendor as sender, recipient, tracking number, simulation mark
            pdf = label.raw
            self.assertTrue(pdf.startswith(b'%PDF'))
            for text in [picking.carrier_tracking_ref, picking._get_shipping_origin_partner().name,
                         picking._get_shipping_destination_partner().city, 'SIMULATION - NOT VALID FOR SHIPPING']:
                self.assertIn(text.encode(), pdf)
            picking.action_update_delivery_state()
            self.assertEqual(picking.delivery_state_code, 'in_transit')
            self.assertEqual(picking.delivery_tracking_message, 'Shipment picked up by driver')
            picking.action_update_delivery_state()
            self.assertEqual(picking.delivery_state_code, 'delivered')
            picking.cancel_shipment()
        self.assertEqual(picking.delivery_state_code, 'canceled')

    def test_simulation_load_products(self):
        self.carrier.delivery_simulation = True
        with self._no_network():
            products = self.carrier._get_sendcloud()._get_shipping_products(from_country='ES')
        self.assertIn('ups:standard', [p['code'] for p in products])

    def test_demo_dropship_with_sendcloud(self):
        order = self.env.ref('delivery_sendcloud_dropship.sale_bistrot_napkins_ups', raise_if_not_found=False)
        if not order:
            self.skipTest('installed without demo data')
        dropship = order.picking_ids.filtered(lambda p: p.picking_type_code == 'dropship')
        self.assertEqual(dropship.carrier_id, order.carrier_id)
        self.assertEqual(order.order_line.filtered('is_delivery').product_id, order.carrier_id.product_id,
                         'shipping method visible on the sale order')
        with self._no_network():
            self._validate(dropship)
        self.assertTrue(dropship.carrier_tracking_ref.startswith('1Z999AA1'))
        self.assertIn('ups.com/track', dropship.carrier_tracking_url)
        self.assertEqual(dropship.delivery_state_code, 'recorded')
        self.assertEqual(dropship.carrier_price, 0, 'free for the customer (free over 0)')
