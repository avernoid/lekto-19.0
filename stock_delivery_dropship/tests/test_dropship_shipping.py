from odoo.tests import Form, TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestDropshipShipping(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Vendor Printing', 'street': 'C/ Moianes 9', 'city': 'Sant Quirze',
            'zip': '08192', 'country_id': cls.env.ref('base.es').id,
        })
        cls.customer = cls.env['res.partner'].create({'name': 'Customer Co', 'is_company': True})
        cls.delivery_address = cls.env['res.partner'].create({
            'type': 'delivery', 'parent_id': cls.customer.id, 'street': '40 Place Paul Asseman',
            'city': 'Dunkerque', 'zip': '59140', 'country_id': cls.env.ref('base.fr').id,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Napkins', 'is_storable': True,
            'route_ids': [(6, 0, cls.env.ref('stock_dropshipping.route_drop_shipping').ids)],
            'seller_ids': [(0, 0, {'partner_id': cls.vendor.id, 'price': 1.0})],
        })
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)

    def _dropship(self, carrier=None):
        order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'partner_shipping_id': self.delivery_address.id,
            'carrier_id': carrier and carrier.id,
            'order_line': [(0, 0, {'product_id': self.product.id, 'product_uom_qty': 10})],
        })
        order.action_confirm()
        purchase = order._get_purchase_orders()
        self.assertEqual(len(purchase), 1)
        purchase.button_confirm()
        picking = purchase.picking_ids
        self.assertEqual(len(picking), 1)
        return order, purchase, picking

    def test_dropship_partners(self):
        order, purchase, picking = self._dropship()
        self.assertEqual(picking.picking_type_code, 'dropship')
        # native behaviour this module works around: the contact of the dropship is the vendor
        self.assertEqual(picking.partner_id, self.vendor)
        self.assertTrue(picking._is_dropship_shipment())
        self.assertTrue(picking._is_customer_shipment())
        self.assertEqual(picking._get_shipping_destination_partner(), self.delivery_address)
        self.assertEqual(picking._get_shipping_origin_partner(), self.vendor)
        self.assertEqual(picking.sale_id, order)

    def test_dropship_without_destination_falls_back_to_contact(self):
        _order, purchase, picking = self._dropship()
        purchase.dest_address_id = False
        self.assertEqual(picking._get_shipping_destination_partner(), picking.partner_id)

    def test_outgoing_partners(self):
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.out_type_id.id,
            'partner_id': self.delivery_address.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        self.assertFalse(picking._is_dropship_shipment())
        self.assertTrue(picking._is_customer_shipment())
        self.assertEqual(picking._get_shipping_destination_partner(), self.delivery_address)
        self.assertEqual(picking._get_shipping_origin_partner(), self.warehouse.partner_id)

    def test_print_label_visible_on_dropship_type(self):
        dropship_type = self.env['stock.picking.type'].search(
            [('code', '=', 'dropship'), ('company_id', '=', self.env.company.id)], limit=1)
        with Form(dropship_type) as form:
            form.print_label = True
        self.assertTrue(dropship_type.print_label)

    def _carrier(self):
        return self.env['delivery.carrier'].create({
            'name': 'UPS', 'delivery_type': 'fixed', 'fixed_price': 0.0,
            'product_id': self.env['product.product'].create({'name': 'UPS shipping', 'type': 'service'}).id,
        })

    def test_dropship_without_option_keeps_native_behaviour(self):
        carrier = self._carrier()
        # option off (the default; the demo data turns it on): standard Odoo behaviour
        self.env['stock.picking.type'].search([('code', '=', 'dropship')]).propagate_sale_carrier = False
        _order, _purchase, picking = self._dropship(carrier)
        self.assertFalse(picking.carrier_id)

    def test_dropship_gets_sale_order_carrier(self):
        carrier = self._carrier()
        self.env['stock.picking.type'].search([('code', '=', 'dropship')]).propagate_sale_carrier = True
        _order, purchase, picking = self._dropship(carrier)
        self.assertEqual(picking.picking_type_id.code, 'dropship')
        self.assertEqual(picking.carrier_id, carrier)
        # still editable on the transfer before validating
        other = self._carrier()
        picking.carrier_id = other
        self.assertEqual(picking.carrier_id, other)

    def test_dropship_option_without_sale_carrier(self):
        self.env['stock.picking.type'].search([('code', '=', 'dropship')]).propagate_sale_carrier = True
        _order, _purchase, picking = self._dropship()
        self.assertFalse(picking.carrier_id)

    def test_demo_dropships_ready(self):
        order = self.env.ref('stock_delivery_dropship.sale_event_napkins', raise_if_not_found=False)
        if not order:
            self.skipTest('installed without demo data')
        dropship = order.picking_ids.filtered(lambda p: p.picking_type_code == 'dropship')
        self.assertEqual(len(dropship), 1)
        self.assertEqual(dropship.state, 'assigned')
        self.assertEqual(dropship.carrier_id, order.carrier_id, 'carrier of the sale order')
        # the shipping method must be visible on the sale order, as its delivery line
        self.assertEqual(order.order_line.filtered('is_delivery').product_id, order.carrier_id.product_id)
        self.assertEqual(dropship._get_shipping_destination_partner(),
                         self.env.ref('stock_delivery_dropship.partner_festival_delivery_address'))
        self.assertEqual(dropship._get_shipping_origin_partner(),
                         self.env.ref('stock_delivery_dropship.partner_vendor_napkins'))
