from odoo.tests.common import TransactionCase

class TestSunatVisibility(TransactionCase):

    def setUp(self):
        super().setUp()
        self.type_dni = self.env['l10n_latam.identification.type'].create({
            'name': 'DNI', 'l10n_pe_vat_code': '1', 'is_vat': False
        })
        self.type_ruc = self.env['l10n_latam.identification.type'].create({
            'name': 'RUC', 'l10n_pe_vat_code': '6', 'is_vat': True
        })
        self.type_other = self.env['l10n_latam.identification.type'].create({
            'name': 'Passport', 'l10n_pe_vat_code': '0', 'is_vat': False
        })

    def test_related_field_logic(self):
        """ Test that l10n_pe_vat_code is correctly related to the identification type """
        partner = self.env['res.partner'].create({'name': 'Test Partner'})

        # Case 1: RUC (Code 6) -> Visible in View
        partner.l10n_latam_identification_type_id = self.type_ruc
        self.assertEqual(partner.l10n_pe_vat_code, '6', "Should inherit code 6 from RUC type")

        # Case 2: DNI (Code 1) -> Visible in View
        partner.l10n_latam_identification_type_id = self.type_dni
        self.assertEqual(partner.l10n_pe_vat_code, '1', "Should inherit code 1 from DNI type")

        # Case 3: Other (Code 0) -> Hidden in View
        partner.l10n_latam_identification_type_id = self.type_other
        self.assertEqual(partner.l10n_pe_vat_code, '0', "Should inherit code 0 from Other type")
