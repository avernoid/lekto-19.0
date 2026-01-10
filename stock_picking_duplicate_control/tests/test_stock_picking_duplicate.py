from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from odoo.tools import mute_logger

class TestStockPickingDuplicate(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Picking = cls.env['stock.picking']
        cls.PickingType = cls.env['stock.picking.type']
        cls.StockMove = cls.env['stock.move']
        cls.Product = cls.env['product.product']

        # Create Products - Updated for Odoo 19 (type='consu' + is_storable=True)
        cls.product_a = cls.Product.create({'name': 'Product A', 'type': 'consu', 'is_storable': True})
        cls.product_b = cls.Product.create({'name': 'Product B', 'type': 'consu', 'is_storable': True})

        # Create Picking Type
        cls.picking_type = cls.PickingType.create({
            'name': 'Test Receipt',
            'code': 'incoming',
            'sequence_code': 'TEST',
            'duplicate_product_policy': 'allow', # Default
        })

    def test_01_policy_allow(self):
        """ Test that duplicates are allowed when policy is 'allow' """
        self.picking_type.duplicate_product_policy = 'allow'
        
        # Create Picking with duplicates
        picking = self.Picking.create({
            'picking_type_id': self.picking_type.id,
            'move_ids': [
                (0, 0, {
                    'product_id': self.product_a.id,
                    'product_uom': self.product_a.uom_id.id,
                    'product_uom_qty': 1,
                    'description_picking': 'Test Desc',
                    'location_id': self.picking_type.default_location_src_id.id or 1,
                    'location_dest_id': self.picking_type.default_location_dest_id.id or 1,
                }),
                (0, 0, {
                    'product_id': self.product_a.id,
                    'product_uom': self.product_a.uom_id.id,
                    'product_uom_qty': 1,
                    'description_picking': 'Test Desc',
                    'location_id': self.picking_type.default_location_src_id.id or 1,
                    'location_dest_id': self.picking_type.default_location_dest_id.id or 1,
                })
            ]
        })
        
        # Should save without error
        self.assertTrue(picking)
        # Banner should be empty/False
        self.assertFalse(picking.duplicate_warning_banner)

    def test_02_policy_warning_banner(self):
        """ Test that duplicates generate a banner when policy is 'warning' """
        self.picking_type.duplicate_product_policy = 'warning'

        picking = self.Picking.create({
            'picking_type_id': self.picking_type.id,
            'move_ids': [
                (0, 0, {
                    'product_id': self.product_a.id,
                    'product_uom_qty': 1,
                    'description_picking': 'Test Desc',
                    'location_id': 1, 'location_dest_id': 1,
                }),
                (0, 0, {
                    'product_id': self.product_a.id,
                    'product_uom_qty': 1,
                    'description_picking': 'Test Desc',
                    'location_id': 1, 'location_dest_id': 1,
                })
            ]
        })

        # Check for banner content
        self.assertTrue(picking.duplicate_warning_banner)
        self.assertIn('alert-warning', picking.duplicate_warning_banner)
        self.assertIn('Product A', picking.duplicate_warning_banner)

    def test_03_policy_block_constraint(self):
        """ Test that duplicates raise ValidationError when policy is 'block' """
        self.picking_type.duplicate_product_policy = 'block'

        with self.assertRaises(ValidationError):
            self.Picking.create({
                'picking_type_id': self.picking_type.id,
                'move_ids': [
                    (0, 0, {
                        'product_id': self.product_a.id,
                        'product_uom_qty': 1,
                        'description_picking': 'Test Desc',
                        'location_id': 1, 'location_dest_id': 1,
                    }),
                    (0, 0, {
                        'product_id': self.product_a.id,
                        'product_uom_qty': 1,
                        'description_picking': 'Test Desc',
                        'location_id': 1, 'location_dest_id': 1,
                    })
                ]
            })

    def test_04_ignore_logic(self):
        """ Test that different descriptions or cancelled lines are ignored """
        self.picking_type.duplicate_product_policy = 'block'

        # Case 1: Different Descriptions
        picking = self.Picking.create({
            'picking_type_id': self.picking_type.id,
            'move_ids': [
                (0, 0, {
                    'product_id': self.product_a.id,
                    'product_uom_qty': 1,
                    'description_picking': 'Desc 1',
                    'location_id': 1, 'location_dest_id': 1,
                }),
                (0, 0, {
                    'product_id': self.product_a.id,
                    'product_uom_qty': 1,
                    'description_picking': 'Desc 2',
                    'location_id': 1, 'location_dest_id': 1,
                })
            ]
        })
        self.assertTrue(picking) # Should allow
        
        # Case 2: Cancelled Line
        # Add a line, cancel it, then add same line again
        move1 = self.StockMove.create({
            'picking_id': picking.id,
            'product_id': self.product_b.id,
            'product_uom_qty': 1,
            'description_picking': 'Desc B',
            'location_id': 1, 'location_dest_id': 1,
        })
        move1._action_cancel()
        
        move2 = self.StockMove.create({
            'picking_id': picking.id,
            'product_id': self.product_b.id,
            'product_uom_qty': 1,
            'description_picking': 'Desc B',
            'location_id': 1, 'location_dest_id': 1,
        })
        self.assertTrue(move2) # Should allow because move1 is cancel

    def test_05_onchange_warning(self):
        """ Test onchange method returning warning """
        self.picking_type.duplicate_product_policy = 'warning'
        
        picking = self.Picking.create({
            'picking_type_id': self.picking_type.id,
            'location_id': 1, 'location_dest_id': 1,
        })
        
        # Create first move
        move1 = self.StockMove.create({
            'picking_id': picking.id,
            'product_id': self.product_a.id,
            'product_uom_qty': 1,
            'description_picking': 'Same Desc',
            'location_id': 1, 'location_dest_id': 1,
        })
        
        # Create second move (simulate user input before save)
        # We manually construct a record to call onchange
        move2 = self.StockMove.create({
            'picking_id': picking.id,
            'product_id': self.product_a.id,
            'description_picking': 'Same Desc', 
            'location_id': 1, 'location_dest_id': 1,
        })
        
        # Call onchange manually
        res = move2._onchange_product_id_check_duplicates()
        self.assertTrue(res)
        self.assertIn('warning', res)
        # Note: Message title might vary slightly based on translations or definitions, checking existence
        self.assertIn('message', res['warning'])

    def test_06_onchange_block(self):
        """ Test onchange method blocking (clearing product) """
        self.picking_type.duplicate_product_policy = 'block'
        
        picking = self.Picking.create({
            'picking_type_id': self.picking_type.id,
            'location_id': 1, 'location_dest_id': 1,
        })
        
        move1 = self.StockMove.create({
            'picking_id': picking.id,
            'product_id': self.product_a.id,
            'description_picking': 'Same Desc',
            'location_id': 1, 'location_dest_id': 1,
        })
        
        move2 = self.StockMove.create({
            'picking_id': picking.id,
            'product_id': self.product_a.id,
            'description_picking': 'Same Desc', 
            'location_id': 1, 'location_dest_id': 1,
        })
        
        res = move2._onchange_product_id_check_duplicates()
        self.assertTrue(res)
        self.assertIn('warning', res)
        # Check if product was cleared (in `self` context of onchange)
        self.assertFalse(move2.product_id)
