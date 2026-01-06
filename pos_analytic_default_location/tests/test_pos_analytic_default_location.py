from odoo.tests.common import TransactionCase
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestPosAnalyticDefaultLocation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        # Setup Analytic
        cls.analytic_plan = cls.env['account.analytic.plan'].create({'name': 'POS Plan'})
        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'POS Analytic',
            'plan_id': cls.analytic_plan.id,
        })
        cls.analytic_distribution = {str(cls.analytic_account.id): 100.0}

        # Setup POS Config
        cls.pos_config = cls.env['pos.config'].create({'name': 'Test POS Store'})
        cls.pos_session = cls.env['pos.session'].create({'config_id': cls.pos_config.id})

        # Setup Product and Accounts
        cls.product = cls.env['product.product'].create({'name': 'POS Product', 'type': 'consu'})
        cls.account_revenue = cls.env['account.account'].create({
            'name': 'Revenue',
            'code': '400001',
            'account_type': 'income',
        })

        # Create Distribution Rules covering POS
        cls.model_pos = cls.env['account.analytic.distribution.model'].create({
            'pos_config_id': cls.pos_config.id,
            'analytic_distribution': cls.analytic_distribution,
        })

    def test_pos_argument_injection(self):
        """ Verify that POS Config ID is injected into arguments when linked to a POS Order """
        
        # 1. Create a mocked POS Order linkage
        # In a real integration test we would run the full POS flow, but for unit testing logic:
        # We need a move linked to a POS Order.
        
        pos_order = self.env['pos.order'].create({
            'name': 'POS/0001',
            'config_id': self.pos_config.id,
            'session_id': self.pos_session.id,
            'amount_tax': 0.0,
            'amount_total': 100.0,
            'amount_paid': 0.0,
            'amount_return': 0.0,
        })
        
        # 2. Create an Account Move linked to the POS Order
        # Odoo usually links via context or move fields. Our logic checks move.pos_order_ids
        # Since pos_order_ids is valid on account.move (One2many), we can set it.
        # However, usually the order links to the invoice (Many2one).
        # Let's check our logic: if self.move_id.pos_order_ids
        
        # We need to set the inverse: pos_order.account_move = move.
        
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2024-01-01',
        })
        
        # Link!
        pos_order.account_move = move.id 
        
        # 3. Create Line
        line = self.env['account.move.line'].create({
            'move_id': move.id,
            'name': 'POS Sale Line',
            'account_id': self.account_revenue.id,
            'product_id': self.product.id,
        })
        
        # 4. Check arguments
        args = line._get_analytic_distribution_arguments(self.env['account.analytic.plan'])
        
        self.assertIn('pos_config_id', args, "POS Config ID missing from arguments")
        self.assertEqual(args['pos_config_id'], self.pos_config.id, "Incorrect POS Config ID in arguments")

    def test_distribution_by_pos_config(self):
        """ Verify automatic assignment by POS Config """
        
        # Setup Move linked to POS
        pos_order = self.env['pos.order'].create({
            'name': 'POS/0002', 
            'config_id': self.pos_config.id, 
            'session_id': self.pos_session.id,
            'amount_tax': 0.0,
            'amount_total': 100.0,
            'amount_paid': 0.0,
            'amount_return': 0.0,
        })
        move = self.env['account.move'].create({'move_type': 'out_invoice', 'date': '2024-01-01'})
        pos_order.account_move = move.id
        
        line = self.env['account.move.line'].create({
            'move_id': move.id,
            'name': 'POS Sale Line',
            'account_id': self.account_revenue.id,
            'product_id': self.product.id,
            'display_type': 'product', # Important to trigger logic
        })
        
        # Compute
        line._compute_analytic_distribution()
        
        # Assert
        self.assertEqual(line.analytic_distribution, self.analytic_distribution, 
                         "Failed to assign analytic distribution based on POS Config")
    def test_pos_priority_in_invoice(self):
        """ Verify that a POS Invoice respects the original POS analytic and doesn't merge with generic rules """
        # Rule 1: Point of Sale match (Specific)
        self.env['account.analytic.distribution.model'].create({
            'pos_config_id': self.pos_config.id,
            'analytic_distribution': self.analytic_distribution,
            'sequence': 1,
        })
        
        # Rule 2: Warehouse match (Generic - would normally apply to this warehouse)
        other_analytic = self.env['account.analytic.account'].create({'name': 'Other', 'plan_id': self.analytic_plan.id})
        other_dist = {str(other_analytic.id): 100.0}
        self.env['account.analytic.distribution.model'].create({
            'origin_warehouse_id': self.pos_config.picking_type_id.warehouse_id.id,
            'analytic_distribution': other_dist,
            'sequence': 100,
        })
        
        # Create POS Order + Invoice
        pos_order = self.env['pos.order'].create({
            'name': 'POS/PRIORITY',
            'config_id': self.pos_config.id,
            'session_id': self.pos_session.id,
            'amount_tax': 0.0,
            'amount_total': 100.0,
            'amount_paid': 0.0,
            'amount_return': 0.0,
        })

        move = self.env['account.move'].create({'move_type': 'out_invoice'})
        pos_order.account_move = move.id # Link
        
        line = self.env['account.move.line'].create({
            'move_id': move.id,
            'name': 'POS Line',
            'product_id': self.product.id,
            'account_id': self.account_revenue.id,
            'display_type': 'product',
        })
        
        line._compute_analytic_distribution()
        
        # Verify: Must have POS Analytic ONLY, not Warehouse Analytic
        self.assertEqual(line.analytic_distribution, self.analytic_distribution, 
                         "POS Invoice incorrectly merged or used Warehouse rules instead of POS rules")
