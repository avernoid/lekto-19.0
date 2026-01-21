from odoo.tests import common, tagged

@tagged('post_install', '-at_install')
class TestStockPickingExtras(common.TransactionCase):

    def setUp(self):
        super(TestStockPickingExtras, self).setUp()
        self.StockPicking = self.env['stock.picking']
        self.StockMoveLine = self.env['stock.move.line']
        self.StockPackage = self.env['stock.package']
        self.Product = self.env['product.product']
        self.StockLocation = self.env['stock.location']
        self.PickingType = self.env['stock.picking.type']
        
        self.product = self.Product.create({'name': 'Test Product', 'type': 'consu'})
        self.location_src = self.StockLocation.create({'name': 'Source'})
        self.location_dest = self.StockLocation.create({'name': 'Dest'})
        
        self.picking_type = self.PickingType.create({
            'name': 'Test Type',
            'code': 'internal',
            'sequence_code': 'TEST',
            'default_location_src_id': self.location_src.id,
            'default_location_dest_id': self.location_dest.id,
        })
        
    def test_packages_and_bundles_computation(self):
        """ Test calculation logic for total_packages and total_bundles """
        picking = self.StockPicking.create({
            'picking_type_id': self.picking_type.id,
            'location_id': self.location_src.id,
            'location_dest_id': self.location_dest.id,
        })
        
        package_a = self.StockPackage.create({'name': 'Pack A'})
        package_b = self.StockPackage.create({'name': 'Pack B'})
        
        # Line 1: in Pack A
        self.StockMoveLine.create({
            'picking_id': picking.id,
            'product_id': self.product.id,
            'quantity': 1.0,
            'result_package_id': package_a.id,
            'location_id': self.location_src.id,
            'location_dest_id': self.location_dest.id,
        })
        
        # Line 2: in Pack A (same package, should not increase package count)
        self.StockMoveLine.create({
            'picking_id': picking.id,
            'product_id': self.product.id,
            'quantity': 1.0,
            'result_package_id': package_a.id,
             'location_id': self.location_src.id,
            'location_dest_id': self.location_dest.id,
        })

        # Line 3: in Pack B (new package)
        self.StockMoveLine.create({
            'picking_id': picking.id,
            'product_id': self.product.id,
            'quantity': 1.0,
            'result_package_id': package_b.id,
             'location_id': self.location_src.id,
            'location_dest_id': self.location_dest.id,
        })
        
        # Line 4: No package, qty 2
        # Should count as 2 bundles
        self.StockMoveLine.create({
            'picking_id': picking.id,
            'product_id': self.product.id,
            'quantity': 2.0,
            'result_package_id': False,
             'location_id': self.location_src.id,
            'location_dest_id': self.location_dest.id,
        })
        
        # Force recompute if necessary, accessing the fields should trigger it
        self.assertEqual(picking.total_packages, 2, "Should have 2 distinct packages (A and B)")
        # Total bundles = 2 (from packages A & B) + 2 (from loose quantity) = 4
        self.assertEqual(picking.total_bundles, 4, "Should have 4 bundles (2 packages + 2 loose units)")
