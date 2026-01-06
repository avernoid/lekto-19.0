from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.tools import frozendict
from odoo import Command

@tagged('post_install', '-at_install')
class TestAccountAnalyticDefault(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        
        # Setup Analytic Plans and Accounts
        cls.analytic_plan = cls.env['account.analytic.plan'].create({'name': 'Plan Test'})
        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'Analytic Test',
            'plan_id': cls.analytic_plan.id,
        })
        cls.analytic_distribution = {str(cls.analytic_account.id): 100.0}

        # Setup Warehouse and Locations
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)
        if not cls.warehouse:
             cls.warehouse = cls.env['stock.warehouse'].create({'name': 'Test WH', 'code': 'TWH'})
        cls.location_src = cls.warehouse.lot_stock_id
        cls.location_dest = cls.env['stock.location'].create({'name': 'Customer', 'usage': 'customer'})

        # Setup Product and Accounts
        cls.product = cls.env['product.product'].create({'name': 'Test Product', 'type': 'consu'})
        cls.account_revenue = cls.env['account.account'].create({
            'name': 'Revenue',
            'code': '400005',
            'account_type': 'income',
        })
        
        # Create Distribution Rules
        cls.model_wh = cls.env['account.analytic.distribution.model'].create({
            'origin_warehouse_id': cls.warehouse.id,
            'analytic_distribution': cls.analytic_distribution,
        })
        
    def test_get_analytic_distribution_arguments_structure(self):
        """ Verify extensibility hook returns expected keys """
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2024-01-01',
        })
        line = self.env['account.move.line'].create({
            'move_id': move.id,
            'name': 'scan line',
            'account_id': self.account_revenue.id,
            'product_id': self.product.id,
        })
        
        # Simulate Stock Move linkage (mocking logic)
        # In a real scenario, this comes from stock_account, but we just need to ensure the method 
        # runs and returns a dict with our keys
        args = line._get_analytic_distribution_arguments(self.env['account.analytic.plan'])
        
        self.assertIn('origin_warehouse_id', args, "Missing origin_warehouse_id in arguments")
        self.assertIn('origin_location_id', args, "Missing origin_location_id in arguments")
        self.assertIn('dest_location_id', args, "Missing dest_location_id in arguments")
        
    def test_distribution_by_warehouse(self):
        """ Verify automatic assignment by Warehouse """
        # We need to simulate a move linked to a picking/stock move
        # Since creating full stock moves is heavy, we can mock the data or 
        # create a move that looks like it came from stock
        
        # 1. Create Picking Type to simulate warehouse
        picking_type = self.env['stock.picking.type'].create({
            'name': 'Delivery',
            'code': 'outgoing',
            'sequence_code': 'OUT',
            'warehouse_id': self.warehouse.id,
        })
        
        # 2. Create Stock Move
        stock_move = self.env['stock.move'].create({
            'product_id': self.product.id,
            'product_uom': self.product.uom_id.id,
            'location_id': self.location_src.id,
            'location_dest_id': self.location_dest.id,
            'picking_type_id': picking_type.id,
        })
        
        # 3. Create Account Move Line linked to this stock move
        # (Odoo uses move_id.stock_move_id usually on the move, let's verify relationship)
        # Actually account.move has stock_move_id field in stock_account module? 
        # checked code: line.move_id.stock_move_id. 
        
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2024-01-01',
            'stock_move_ids': [Command.set(stock_move.ids)], # Link at header level
        })
        
        line = self.env['account.move.line'].create({
            'move_id': move.id,
            'name': 'Stock Journal Item',
            'account_id': self.account_revenue.id,
            'product_id': self.product.id,
            'display_type': 'product',
        })
        
        # Trigger computation
        line._compute_analytic_distribution()
        
        # Assert
        self.assertEqual(line.analytic_distribution, self.analytic_distribution, 
                         "Failed to assign analytic distribution based on Warehouse")
