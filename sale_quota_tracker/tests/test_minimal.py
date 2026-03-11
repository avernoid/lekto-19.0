from odoo.tests.common import TransactionCase


class TestSaleQuotaMinimal(TransactionCase):

    def test_minimal(self):
        """Minimal smoke test: verifies sale.goal model is accessible."""
        SaleGoal = self.env['sale.goal']
        self.assertTrue(SaleGoal._name == 'sale.goal', 'sale.goal model must be accessible')
