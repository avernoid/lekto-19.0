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
