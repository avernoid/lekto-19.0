from odoo.tests.common import TransactionCase
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestAnalyticDistribution(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Setup Analytic
        cls.analytic_plan = cls.env['account.analytic.plan'].create({'name': 'Test Plan'})
        cls.analytic_account_1 = cls.env['account.analytic.account'].create({
            'name': 'Analytic 1',
            'plan_id': cls.analytic_plan.id,
        })
        cls.analytic_account_2 = cls.env['account.analytic.account'].create({
            'name': 'Analytic 2',
            'plan_id': cls.analytic_plan.id,
        })
        cls.dist_1 = {str(cls.analytic_account_1.id): 100.0}
        cls.dist_2 = {str(cls.analytic_account_2.id): 100.0}

        # Setup Dimension Data
        cls.warehouse = cls.env['stock.warehouse'].create({'name': 'Test WH', 'code': 'TWH'})
        cls.journal = cls.env['account.journal'].create({'name': 'Test Journal', 'type': 'general', 'code': 'TJ'})
        cls.product = cls.env['product.product'].create({'name': 'Test Product', 'type': 'consu'})
        cls.salesperson = cls.env['res.users'].create({'name': 'Salesperson A', 'login': 'sales_a', 'email': 'a@a.com'})

    def test_01_account_prefix_matching(self):
        """ Verify that partial prefixes match correctly """
        self.env['account.analytic.distribution.model'].create({
            'account_prefix': '60',
            'analytic_distribution': self.dist_1,
            'sequence': 10,
        })
        res = self.env['account.analytic.distribution.model']._get_distribution({'account_prefix': '601100'})
        self.assertEqual(res, self.dist_1)

    def test_02_supreme_priority_so_to_invoice(self):
        """ Verify that SO analytic distribution takes absolute priority in Invoices (No Merging) """
        # Rule: Warehouse match
        self.env['account.analytic.distribution.model'].create({
            'origin_warehouse_id': self.warehouse.id,
            'analytic_distribution': self.dist_1,
            'sequence': 1,
        })
        
        # Create Sale Order with Analytic Account 2 (Manual Choice)
        sale_order = self.env['sale.order'].create({
            'partner_id': self.env.ref('base.res_partner_1').id,
            'warehouse_id': self.warehouse.id,
        })
        so_line = self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': self.product.id,
            'analytic_distribution': self.dist_2,
        })
        
        # Invoicing
        invoice = sale_order._create_invoices()
        inv_line = invoice.invoice_line_ids[0]
        
        # Verify: Invoice has DIST_2 (from SO) and NOT DIST_1 (from Warehouse Rule)
        self.assertEqual(inv_line.analytic_distribution, self.dist_2, "Invoice should respect SO choice and ignore generic Warehouse rules")

    def test_03_manual_override_protection(self):
        """ Verify that manual edits are not overwritten by header changes (Odoo standard) """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.env.ref('base.res_partner_1').id,
            'warehouse_id': self.warehouse.id,
        })
        so_line = self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': self.product.id,
        })
        
        # Let's say it auto-filled with something (or empty). User sets DIST_2.
        so_line.analytic_distribution = self.dist_2
        
        # Simulate trigger: Change Warehouse in header
        warehouse_2 = self.env['stock.warehouse'].create({'name': 'WH 2', 'code': 'WH2'})
        sale_order.warehouse_id = warehouse_2.id
        
        # Recompute triggers via depends
        so_line._compute_analytic_distribution()
        
        # Verify: Distribution STAYS as DIST_2 (Manual Entry Protection)
        self.assertEqual(so_line.analytic_distribution, self.dist_2, "Manual distribution was incorrectly overwritten by warehouse change")

    def test_04_reset_to_default_self_healing(self):
        """ Verify that clearing the field allows the system to re-apply the best default """
        self.env['account.analytic.distribution.model'].create({
            'origin_warehouse_id': self.warehouse.id,
            'analytic_distribution': self.dist_1,
        })
        
        sale_order = self.env['sale.order'].create({
            'partner_id': self.env.ref('base.res_partner_1').id,
            'warehouse_id': self.warehouse.id,
        })
        so_line = self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': self.product.id,
        })
        so_line.analytic_distribution = self.dist_2 # User changed it
        
        # Now User CLEARS it (Empty intent)
        so_line.analytic_distribution = False
        so_line._compute_analytic_distribution()
        
        # Verify: System "Self-heals" and puts the Warehouse default back
        self.assertEqual(so_line.analytic_distribution, self.dist_1, "Clearing the field should allow re-application of defaults")

    def test_05_salesperson_matching(self):
        """ Verify that salesperson (user_id) is used in matching """
        self.env['account.analytic.distribution.model'].create({
            'invoice_user_id': self.salesperson.id, # Salesperson field in model
            'analytic_distribution': self.dist_1,
        })
        
        sale_order = self.env['sale.order'].create({
            'partner_id': self.env.ref('base.res_partner_1').id,
            'user_id': self.salesperson.id, # Salesperson in SO
        })
        so_line = self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': self.product.id,
        })
        
        # Recompute
        so_line._compute_analytic_distribution()
        
        # Verify
        self.assertEqual(so_line.analytic_distribution, self.dist_1, "Rule for Salesperson failed to apply to SO line")

    def test_06_multi_account_prefix_matching(self):
        """ Verify that comma-separated account prefixes match correctly """
        self.env['account.analytic.distribution.model'].create({
            'account_prefix': '40, 60, 64',
            'analytic_distribution': self.dist_1,
            'sequence': 10,
        })
        
        # Match with 40
        res_40 = self.env['account.analytic.distribution.model']._get_distribution({'account_prefix': '401100'})
        self.assertEqual(res_40, self.dist_1, "Failed to match prefix '40' in multi-prefix rule")
        
        # Match with 64
        res_64 = self.env['account.analytic.distribution.model']._get_distribution({'account_prefix': '641000'})
        self.assertEqual(res_64, self.dist_1, "Failed to match prefix '64' in multi-prefix rule")
        
        # Should NOT match with 70
        res_70 = self.env['account.analytic.distribution.model']._get_distribution({'account_prefix': '701000'})
        self.assertEqual(res_70, {}, "Rule incorrectly matched prefix '70'")

    def test_07_odoo_merging_logic_different_plans(self):
        """ Verify that rules for different plans merge correctly (Odoo 19 standard) """
        # Plan 2 setup
        plan_2 = self.env['account.analytic.plan'].create({'name': 'Plan 2'})
        account_p2 = self.env['account.analytic.account'].create({
            'name': 'Account P2',
            'plan_id': plan_2.id,
        })
        dist_p2 = {str(account_p2.id): 100.0}

        # Rule 1: Specific to Salesperson (Plan 1)
        self.env['account.analytic.distribution.model'].create({
            'invoice_user_id': self.salesperson.id,
            'analytic_distribution': self.dist_1,
            'sequence': 10,
        })
        
        # Rule 2: Specific to Warehouse (Plan 2)
        self.env['account.analytic.distribution.model'].create({
            'origin_warehouse_id': self.warehouse.id,
            'analytic_distribution': dist_p2,
            'sequence': 20,
        })
        
        # Simulate arguments with BOTH criteria
        args = {
            'invoice_user_id': self.salesperson.id,
            'origin_warehouse_id': self.warehouse.id,
        }
        
        res = self.env['account.analytic.distribution.model']._get_distribution(args)
        
        # Verify: Merged! 
        expected = {}
        expected.update(self.dist_1)
        expected.update(dist_p2)
        self.assertEqual(res, expected, "Analytic distributions for different plans should merge in Odoo 19")

