from odoo.tests import common
from odoo.exceptions import AccessError

class TestSunatCatalogs(common.TransactionCase):

    def setUp(self):
        super(TestSunatCatalogs, self).setUp()
        self.charge_discount_model = self.env['charge.discount.codes']
        self.classification_services_model = self.env['classification.services']
        self.payment_methods_model = self.env['payment.methods.codes']

    def test_01_charge_discount_codes(self):
        """ Test catalog 53: Charge and Discount Codes """
        record = self.charge_discount_model.create({
            'code': '99',
            'description': 'Test Charge'
        })
        self.assertEqual(record.name, '[99] Test Charge')
        
    def test_02_classification_services(self):
        """ Test catalog 30: Classification of Services """
        record = self.classification_services_model.create({
            'code': '001',
            'description': 'Test Service'
        })
        self.assertEqual(record.display_name, '001 Test Service')

    def test_03_payment_methods(self):
        """ Test catalog 59: Payment Methods """
        record = self.payment_methods_model.create({
            'code': '001',
            'description': 'Test Payment Method'
        })
        # Verify creation and field existence
        self.assertTrue(record.id)
        self.assertEqual(record.code, '001')
