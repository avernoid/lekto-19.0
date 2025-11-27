from odoo.tests.common import TransactionCase, tagged

@tagged('post_install', '-at_install')
class TestSaleOneStepInvoice(TransactionCase):

    def setUp(self):
        super(TestSaleOneStepInvoice, self).setUp()
        self.team = self.env['crm.team'].create({
            'name': 'Test Team',
        })
        self.partner = self.env['res.partner'].create({
            'name': 'Test Partner',
        })
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 100.0,
            'type': 'consu',
            'invoice_policy': 'order',
        })

    def create_sale_order(self):
        return self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'team_id': self.team.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
            })],
        })

    def test_standard_behavior(self):
        """Test that standard behavior (wizard) is preserved when flags are off."""
        self.team.skip_invoice_wizard = False
        self.team.create_posted_invoice = False
        
        order = self.create_sale_order()
        order.action_confirm()
        
        action = order.action_create_invoice()
        self.assertTrue(isinstance(action, dict))
        self.assertEqual(action.get('type'), 'ir.actions.act_window')
        self.assertEqual(action.get('res_model'), 'sale.advance.payment.inv')
        
        self.assertFalse(order.invoice_ids)

    def test_skip_wizard(self):
        """Test that wizard is skipped and draft invoice created."""
        self.team.skip_invoice_wizard = True
        self.team.create_posted_invoice = False
        
        order = self.create_sale_order()
        order.action_confirm()
        
        order.action_create_invoice()
        
        self.assertTrue(order.invoice_ids)
        self.assertEqual(len(order.invoice_ids), 1)
        self.assertEqual(order.invoice_ids.state, 'draft')

    def test_create_posted_invoice_auto(self):
        """Test that invoice is posted automatically when skipping wizard."""
        self.team.skip_invoice_wizard = True
        self.team.create_posted_invoice = True
        
        order = self.create_sale_order()
        order.action_confirm()
        
        order.action_create_invoice()
        
        self.assertTrue(order.invoice_ids)
        self.assertEqual(len(order.invoice_ids), 1)
        self.assertEqual(order.invoice_ids.state, 'posted')

    def test_create_posted_invoice_manual(self):
        """Test that invoice is posted automatically even when using the wizard (manual flow)."""
        self.team.skip_invoice_wizard = False
        self.team.create_posted_invoice = True
        
        order = self.create_sale_order()
        order.action_confirm()
        
        # 1. Trigger the button (returns wizard action)
        action = order.action_create_invoice()
        self.assertEqual(action.get('res_model'), 'sale.advance.payment.inv')
        
        # 2. Simulate user clicking "Create Invoice" in the wizard
        # We need to create the wizard manually as the UI would
        wizard = self.env['sale.advance.payment.inv'].with_context(active_ids=order.ids, active_model='sale.order').create({
            'advance_payment_method': 'delivered',
        })
        wizard.create_invoices()
        
        # 3. Verify invoice is posted
        self.assertTrue(order.invoice_ids)
        self.assertEqual(len(order.invoice_ids), 1)
        self.assertEqual(order.invoice_ids.state, 'posted')
