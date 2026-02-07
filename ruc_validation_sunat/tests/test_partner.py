from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError

class TestResPartner(TransactionCase):

    def setUp(self):
        super(TestResPartner, self).setUp()
        self.ResPartner = self.env['res.partner']
        self.ResCompany = self.env['res.company']
        self.company = self.env.user.company_id
        self.company.write({'token_api_ruc': 'your_token_api_ruc'})

        self.partner = self.ResPartner.create({
            'name': 'Test Partner',
            'vat': '12345678901',
            'l10n_latam_identification_type_id': self.env.ref('l10n_latam_base.it_vat').id,
            'company_id': self.company.id,
        })
        print("------------------SET UP---------------------------")

    def test_handle_data_sunat_no_token(self):
        self.company.write({'token_api_ruc': False})
        with self.assertRaises(UserError):
            self.partner.handle_data_sunat({'vat': '12345678901', 'l10n_latam_identification_type_id': self.env.ref('l10n_latam_base.it_vat').id})
        print("------------------TEST 1---------------------------")

    def test_handle_data_sunat_with_token(self):
        self.company.write({'token_api_ruc': 'your_token_api_ruc'})
        partner_data = {'vat': '12345678901', 'l10n_latam_identification_type_id': self.env.ref('l10n_latam_base.it_vat').id}
        values = self.partner.handle_data_sunat(partner_data)
        self.assertFalse(values)
        print("------------------TEST 2---------------------------")

    def test_action_validate_sunat(self):
        partner_data = {'vat': '12345678901', 'l10n_latam_identification_type_id': self.env.ref('l10n_latam_base.it_vat').id}
        partner_id = self.partner.action_validate_sunat(partner_data)
        self.assertFalse(partner_id)
        print("------------------TEST 3---------------------------")

    def test_action_ruc_validation_sunat(self):
        self.company.write({'token_api_ruc': 'your_token_api_ruc'})
        with self.assertRaises(ValidationError):
            self.partner.action_ruc_validation_sunat()
        print("------------------TEST 4---------------------------")
