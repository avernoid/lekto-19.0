from odoo.tests.common import TransactionCase

class TestSaleLostReason(TransactionCase):

    def setUp(self):
        super(TestSaleLostReason, self).setUp()
        self.lost_reason = self.env['sale.lost.reason'].create({
            'name': 'Too Expensive',
        })
        self.partner = self.env['res.partner'].create({'name': 'Test Partner'})

    def test_create_lost_reason(self):
        """Test that a lost reason can be created."""
        self.assertTrue(self.lost_reason.id, "Lost reason should be created")
        self.assertEqual(self.lost_reason.name, 'Too Expensive', "Lost reason name should be correct")
        self.assertTrue(self.lost_reason.active, "Lost reason should be active by default")

    def test_assign_lost_reason_to_order(self):
        """Test assigning a lost reason to a sale order."""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'lost_reason_id': self.lost_reason.id,
        })
        self.assertEqual(sale_order.lost_reason_id, self.lost_reason, "Lost reason should be assigned to the order")

    def test_action_cancel_wizard_trigger(self):
        """Test that the wizard is triggered when cancelling an order if 'Use Lost Reason' is enabled."""
        # Enable 'Use Lost Reason' on the sales team
        self.env['crm.team'].search([]).write({'use_lost_reason': False}) # Reset all
        team = self.env['crm.team'].create({'name': 'Test Team', 'use_lost_reason': True})

        # Create a sale order
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'team_id': team.id,
        })

        # Call action_cancel and check if it returns the wizard action
        action = sale_order.action_cancel()
        self.assertIsInstance(action, dict, "Should return a dictionary (wizard action)")
        self.assertEqual(action.get('res_model'), 'sale.lost.reason.wizard', "Should return the lost reason wizard")

        # Create the wizard and confirm
        wizard = self.env['sale.lost.reason.wizard'].with_context(active_id=sale_order.id).create({
            'lost_reason_id': self.lost_reason.id,
        })
        wizard.action_confirm()

        # Check if the order is cancelled and the lost reason is set
        self.assertEqual(sale_order.state, 'cancel', "Order should be cancelled")
        self.assertEqual(sale_order.lost_reason_id, self.lost_reason, "Lost reason should be set")
