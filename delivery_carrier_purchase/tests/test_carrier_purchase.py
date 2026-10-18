from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import Form, TransactionCase, tagged

from odoo.addons.delivery_carrier_purchase.models.stock_picking import StockPicking

LOGGER = 'odoo.addons.delivery_carrier_purchase.models.stock_picking'


@tagged('post_install', '-at_install')
class TestCarrierPurchase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.write({'carrier_purchase': True, 'carrier_purchase_grouping': 'month'})
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.company.id)], limit=1)
        cls.customer = cls.env['res.partner'].create({
            'name': 'Hotel Customer', 'zip': '08013', 'city': 'Barcelona', 'country_id': cls.env.ref('base.es').id,
        })
        cls.carrier_vendor = cls.env['res.partner'].create({'name': 'Courier Company'})
        cls.product = cls.env['product.product'].create({'name': 'Cups', 'type': 'consu', 'weight': 2.0})
        cls.shipping_product = cls.env['product.product'].create({'name': 'Shipping', 'type': 'service'})
        cls.carrier = cls.env['delivery.carrier'].create({
            'name': 'Courier 24h', 'delivery_type': 'fixed', 'fixed_price': 0.0,
            'product_id': cls.shipping_product.id,
            'purchase_partner_id': cls.carrier_vendor.id,
            'purchase_cost_type': 'fixed', 'purchase_fixed_cost': 6.40,
        })

    def _delivery(self, carrier=None, partner=None):
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.out_type_id.id,
            'partner_id': (partner or self.customer).id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'carrier_id': (carrier or self.carrier).id,
            'move_ids': [(0, 0, {
                'name': 'Cups', 'product_id': self.product.id, 'product_uom_qty': 3,
                'location_id': self.warehouse.lot_stock_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            })],
        })
        picking.action_confirm()
        return picking

    def _validate(self, picking):
        picking.move_ids.quantity = picking.move_ids.product_uom_qty
        picking.move_ids.picked = True
        picking._action_done()
        self.assertEqual(picking.state, 'done')
        return picking

    def _ship(self, carrier=None, partner=None):
        return self._validate(self._delivery(carrier, partner))

    # ------------------------------------------------------------------ #

    def test_shipments_accumulate_in_open_rfq(self):
        first, second = self._ship(), self._ship()
        line1, line2 = first.carrier_purchase_line_id, second.carrier_purchase_line_id
        self.assertTrue(line1 and line2)
        self.assertNotEqual(line1, line2, 'one line per shipment')
        order = line1.order_id
        self.assertEqual(line2.order_id, order, 'same open request for quotation')
        self.assertEqual(order.partner_id, self.carrier_vendor)
        self.assertEqual(order.state, 'draft')
        self.assertTrue(order.carrier_purchase_period)
        self.assertEqual(line1.price_unit, 6.40)
        self.assertEqual(line1.product_qty, 1)
        self.assertEqual(line1.product_id, self.shipping_product)
        # links both ways
        self.assertEqual(line1.carrier_picking_ids, first)
        self.assertEqual(first.carrier_purchase_id, order)
        self.assertEqual(order.carrier_picking_count, 2)
        self.assertEqual(set(order.action_view_carrier_pickings()['domain'][0][2]), {first.id, second.id})
        # description to check the carrier bill
        self.assertIn(first.name, line1.name)
        self.assertIn('Courier 24h', line1.name)
        self.assertIn('08013 Barcelona, ES', line1.name)

    def test_confirmed_rfq_gets_no_more_lines(self):
        order = self._ship().carrier_purchase_id
        order.button_confirm()
        self.assertEqual(order.state, 'purchase')
        self.assertNotEqual(self._ship().carrier_purchase_id, order)

    def test_one_purchase_per_shipment(self):
        self.company.carrier_purchase_grouping = 'shipment'
        first, second = self._ship(), self._ship()
        self.assertNotEqual(first.carrier_purchase_id, second.carrier_purchase_id)
        self.assertEqual(first.carrier_purchase_id.carrier_purchase_period, first.name)

    def test_period_keys(self):
        picking = self._ship()
        day = picking.date_done.date()
        for grouping, expected in [('month', day.strftime('%Y-%m')), ('day', day.isoformat()),
                                   ('week', '%s-W%02d' % day.isocalendar()[:2])]:
            self.company.carrier_purchase_grouping = grouping
            self.assertEqual(picking._get_carrier_purchase_period(), expected)

    def test_nothing_when_disabled_or_not_configured(self):
        self.company.carrier_purchase = False
        self.assertFalse(self._ship().carrier_purchase_line_id)
        self.company.carrier_purchase = True
        no_vendor = self.carrier.copy({'purchase_partner_id': False})
        self.assertFalse(self._ship(no_vendor).carrier_purchase_line_id)

    def test_receipts_are_not_shipments(self):
        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.in_type_id.id,
            'partner_id': self.customer.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
            'carrier_id': self.carrier.id,
            'move_ids': [(0, 0, {
                'name': 'Cups', 'product_id': self.product.id, 'product_uom_qty': 1,
                'location_id': self.env.ref('stock.stock_location_suppliers').id,
                'location_dest_id': self.warehouse.lot_stock_id.id,
            })],
        })
        receipt.action_confirm()
        self.assertFalse(self._validate(receipt).carrier_purchase_line_id)

    def test_cost_error_creates_line_at_zero(self):
        with patch.object(type(self.env['delivery.carrier']), '_get_carrier_purchase_cost',
                          side_effect=UserError('Carrier API down')):
            picking = self._ship()
        line = picking.carrier_purchase_line_id
        self.assertTrue(line)
        self.assertEqual(line.price_unit, 0.0)
        self.assertIn('Carrier API down', picking.carrier_purchase_error)
        self.assertIn('Carrier API down', line.order_id.message_ids[0].body)

    def test_line_error_never_blocks_validation(self):
        with patch.object(StockPicking, '_get_carrier_purchase_order', side_effect=ValueError('no vendor data')), \
                self.assertLogs(LOGGER, 'WARNING') as logs:
            picking = self._ship()
        self.assertEqual(picking.state, 'done')
        self.assertFalse(picking.carrier_purchase_line_id)
        self.assertIn('no vendor data', picking.carrier_purchase_error)
        self.assertIn('not created', logs.output[0])
        self.assertTrue(picking.activity_ids)
        # once fixed, the button creates it
        picking.action_create_carrier_purchase()
        self.assertTrue(picking.carrier_purchase_line_id)

    def test_cost_types(self):
        carrier = self.carrier
        picking = self._ship()
        self.assertEqual(carrier._get_carrier_purchase_cost(picking), 6.40)
        # vendor price list
        self.shipping_product.seller_ids = [(0, 0, {'partner_id': self.carrier_vendor.id, 'price': 48.5})]
        carrier.purchase_cost_type = 'vendor'
        self.assertEqual(carrier._get_carrier_purchase_cost(picking), 48.5)
        carrier.purchase_partner_id = self.env['res.partner'].create({'name': 'Other vendor'})
        with self.assertRaises(UserError):
            carrier._get_carrier_purchase_cost(picking)
        # shipment cost: price of the fixed method, or what the carrier returned
        carrier.write({'purchase_cost_type': 'shipment', 'fixed_price': 7.0})
        self.assertEqual(carrier._get_carrier_purchase_cost(picking), 7.0)
        picking.carrier_purchase_cost = 5.25
        self.assertEqual(carrier._get_carrier_purchase_cost(picking), 7.0, 'fixed: price of the method')
        with patch.object(type(carrier), '_keeps_shipment_cost', lambda c: True):
            self.assertEqual(carrier._get_carrier_purchase_cost(picking), 5.25)

    def test_rule_cost_uses_real_destination_and_weight(self):
        carrier = self.env['delivery.carrier'].create({
            'name': 'GLS by weight', 'delivery_type': 'base_on_rule',
            'product_id': self.shipping_product.id, 'purchase_partner_id': self.carrier_vendor.id,
            'country_ids': [(6, 0, self.env.ref('base.es').ids)],
            'price_rule_ids': [
                (0, 0, {'variable': 'weight', 'operator': '<=', 'max_value': 5, 'list_base_price': 5.9}),
                (0, 0, {'variable': 'weight', 'operator': '<=', 'max_value': 20, 'list_base_price': 8.4}),
            ],
        })
        picking = self._ship(carrier)  # 3 x 2 kg
        self.assertEqual(picking.carrier_purchase_line_id.price_unit, 8.4)
        foreign = self.env['res.partner'].create({'name': 'Bistrot', 'country_id': self.env.ref('base.fr').id})
        picking = self._delivery(carrier, foreign)
        with self.assertRaises(UserError):
            carrier._get_carrier_purchase_cost(picking)

    def test_integrated_carrier_cost_is_kept(self):
        """What the carrier charges is kept even when the shipping is free for the customer."""
        model = type(self.env['delivery.carrier'])
        self.warehouse.out_type_id.print_label = True
        self.carrier.write({'purchase_cost_type': 'shipment', 'free_over': True, 'amount': 0})

        def send_shipping(carrier, pickings):
            return [{'exact_price': 6.90, 'tracking_number': '1Z999AA10123456784'} for _picking in pickings]

        # the fixed method behaves here like a carrier integration
        with patch.object(model, 'fixed_send_shipping', send_shipping),                 patch.object(model, '_keeps_shipment_cost', lambda carrier: True):
            picking = self._ship()
        self.assertEqual(picking.carrier_tracking_ref, '1Z999AA10123456784')
        self.assertEqual(picking.carrier_purchase_cost, 6.90)
        self.assertEqual(picking.carrier_purchase_line_id.price_unit, 6.90)
        self.assertIn('1Z999AA10123456784', picking.carrier_purchase_line_id.name)

    def test_tracking_reference_updates_description(self):
        picking = self._ship()
        picking.carrier_tracking_ref = 'GLS123456789'
        self.assertIn('GLS123456789', picking.carrier_purchase_line_id.name)

    def test_cancel_at_carrier_keeps_line_at_zero(self):
        picking = self._ship()
        picking.carrier_tracking_ref = 'GLS123456789'
        line = picking.carrier_purchase_line_id
        with patch.object(type(self.env['delivery.carrier']), 'fixed_cancel_shipment', lambda c, p: None):
            picking.cancel_shipment()
        self.assertTrue(line.exists())
        self.assertEqual(line.price_unit, 0.0)
        self.assertTrue(line.name.startswith('CANCELLED'))
        self.assertIn('GLS123456789', line.name, 'the cancelled line keeps the tracking reference')
        self.assertTrue(picking.carrier_purchase_canceled)
        self.assertFalse(picking.carrier_tracking_ref)

    def test_failed_carrier_cancel_leaves_line(self):
        picking = self._ship()
        with self.assertRaises(NotImplementedError):
            picking.cancel_shipment()  # fixed methods cannot cancel at the carrier
        self.assertEqual(picking.carrier_purchase_line_id.price_unit, 6.40)

    def test_cancel_wizard(self):
        picking = self._ship()
        action = picking.action_cancel_carrier_purchase()
        wizard = Form(self.env[action['res_model']].with_context(action['context']))
        wizard.reason = 'Shipment repeated'
        wizard.save().action_confirm()
        line = picking.carrier_purchase_line_id
        self.assertEqual(line.price_unit, 0.0)
        self.assertIn('CANCELLED: Shipment repeated', line.name)
        # twice does nothing more
        picking._cancel_carrier_purchase('again')
        self.assertEqual(line.name.count('CANCELLED'), 1)

    def test_billed_line_is_not_cancelled(self):
        picking = self._ship()
        line = picking.carrier_purchase_line_id
        line.order_id.button_confirm()
        line.qty_received = 1
        line.order_id.action_create_invoice()
        self.assertEqual(line.qty_invoiced, 1)
        picking._cancel_carrier_purchase('late')
        self.assertEqual(line.price_unit, 6.40)
        self.assertFalse(picking.carrier_purchase_canceled)
        self.assertIn('credit note', picking.message_ids[0].body)

    def test_no_double_purchase_with_delivery_product(self):
        """Transition: a sale whose delivery product already created the transport purchase."""
        self.shipping_product.write({
            'seller_ids': [(0, 0, {'partner_id': self.carrier_vendor.id, 'price': 0})],
            'service_to_purchase': True,
        })
        order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [(0, 0, {'product_id': self.product.id, 'product_uom_qty': 3})],
        })
        order.set_delivery_line(self.carrier, 0.0)
        order.action_confirm()
        self.assertTrue(order.order_line.filtered('is_delivery').purchase_line_ids)
        picking = order.picking_ids
        self.assertEqual(picking.carrier_id, self.carrier)
        self._validate(picking)
        self.assertFalse(picking.carrier_purchase_line_id)

    def test_dropship_is_bought(self):
        vendor = self.env['res.partner'].create({'name': 'Printing vendor'})
        product = self.env['product.product'].create({
            'name': 'Napkins', 'is_storable': True,
            'route_ids': [(6, 0, self.env.ref('stock_dropshipping.route_drop_shipping').ids)],
            'seller_ids': [(0, 0, {'partner_id': vendor.id, 'price': 1.0})],
        })
        order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [(0, 0, {'product_id': product.id, 'product_uom_qty': 10})],
        })
        order.action_confirm()
        purchase = order._get_purchase_orders()
        purchase.button_confirm()
        dropship = purchase.picking_ids
        dropship.carrier_id = self.carrier
        self._validate(dropship)
        line = dropship.carrier_purchase_line_id
        self.assertTrue(line)
        self.assertEqual(line.order_id.partner_id, self.carrier_vendor)
        self.assertIn('Barcelona', line.name, 'destination of the dropship, not the vendor')
        self.assertIn(order.name, line.name)

    def test_warnings_for_purchase_automatically(self):
        self.shipping_product.write({
            'seller_ids': [(0, 0, {'partner_id': self.carrier_vendor.id, 'price': 0})],
            'service_to_purchase': True,
        })
        self.carrier.invalidate_recordset(['purchase_auto_warning'])
        self.assertTrue(self.carrier.purchase_auto_warning)
        settings = self.env['res.config.settings'].create({})
        self.assertIn('Shipping', settings.carrier_purchase_auto_products)
        self.company.carrier_purchase = False
        self.carrier.invalidate_recordset(['purchase_auto_warning'])
        self.assertFalse(self.carrier.purchase_auto_warning)


@tagged('post_install', '-at_install')
class TestCarrierPurchaseDemo(TransactionCase):

    def test_demo_dropships_buy_their_transport(self):
        demo = self.env.ref('delivery_carrier_purchase.sale_festival_cups_gls', raise_if_not_found=False)
        if not demo:
            self.skipTest('installed without demo data')
        for xmlid, vendor_xmlid in [('sale_festival_cups_gls', 'partner_vendor_gls'),
                                    ('sale_festival_tote_bags_pallet', 'partner_vendor_palletways')]:
            order = self.env.ref('delivery_carrier_purchase.%s' % xmlid)
            dropship = order._get_purchase_orders().picking_ids
            self.assertEqual(len(dropship), 1)
            self.assertEqual(dropship.carrier_id, order.carrier_id)
            self.assertEqual(order.order_line.filtered('is_delivery').product_id, order.carrier_id.product_id,
                             'shipping method visible on the sale order')
            dropship.move_ids.quantity = dropship.move_ids.product_uom_qty
            dropship.move_ids.picked = True
            dropship.button_validate()
            line = dropship.carrier_purchase_line_id
            self.assertTrue(line, xmlid)
            self.assertFalse(dropship.carrier_purchase_error, xmlid)
            self.assertGreater(line.price_unit, 0)
            self.assertEqual(line.order_id.partner_id, self.env.ref('delivery_carrier_purchase.%s' % vendor_xmlid))
