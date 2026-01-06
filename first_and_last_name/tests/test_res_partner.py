from odoo.tests.common import TransactionCase

class TestResPartner(TransactionCase):
    def setUp(self):
        super(TestResPartner, self).setUp()
        self.partner = self.env['res.partner'].create({
            'name': 'John Doe Smith',
            'partner_name': 'John',
            'first_name': 'Doe',
            'second_name': 'Smith'
        })
        print("SET UP")

    def test_partner_fields_independence(self):
        """ Verify that detail fields and the standard name field remain independent """
        self.partner.write({'name': 'Different Name'})
        self.assertEqual(self.partner.partner_name, 'John', "partner_name should NOT have changed")
        
        self.partner.write({'partner_name': 'Mark'})
        self.assertEqual(self.partner.name, 'Different Name', "name field should NOT have changed")
