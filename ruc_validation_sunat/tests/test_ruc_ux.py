from odoo.tests.common import TransactionCase, Form

class TestRucUx(TransactionCase):

    def test_onchange_vat_prefills_name(self):
        """ Test that entering VAT pre-fills the Name if empty """
        partner_form = Form(self.env['res.partner'])
        # Simulator user entering VAT
        partner_form.vat = '20543212345'
        
        # Check if name was populated with VAT
        self.assertEqual(partner_form.name, '20543212345', "Name should be pre-filled with VAT")

    def test_onchange_vat_respects_existing_name(self):
        """ Test that entering VAT does NOT overwrite existing Name """
        partner_form = Form(self.env['res.partner'])
        # Simulator user entering Name first
        partner_form.name = 'My Company SAC'
        partner_form.vat = '20543212345'
        
        # Check if name was preserved
        self.assertEqual(partner_form.name, 'My Company SAC', "Existing Name should NOT be overwritten")
