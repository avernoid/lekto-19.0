from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestTributaryAddressExtension(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ResPartner = cls.env['res.partner']
        cls.country_pe = cls.env.ref('base.pe')
        cls.country_mx = cls.env.ref('base.mx')

    def setUp(self):
        super().setUp()
        self.partner = self.ResPartner.create({'name': 'Test Partner'})
        self.env.company.country_id = self.country_pe

    def test_annexed_establishment_default_value(self):
        self.assertEqual(
            self.partner.annexed_establishment, '0000',
            'El valor predeterminado no está configurado correctamente.'
        )
        print("TEST OK")

    def test_annexed_establishment_change_value(self):
        new_value = '5678'
        self.partner.write({'annexed_establishment': new_value})
        self.assertEqual(
            self.partner.annexed_establishment, new_value,
            'El valor del establecimiento anexo no se modificó correctamente.'
        )
        print("TEST OK")

    def test_annexed_establishment_visible_form_view(self):
        arch, view = self.ResPartner._get_view()
        arch_annexed_establishment = arch.xpath("//field[@name='annexed_establishment']")
        self.assertFalse(
            'invisible' in arch_annexed_establishment[0].attrib,
            "El campo 'annexed_establishment' no debe estar invisible."
        )
        print("TEST OK")

    def test_annexed_establishment_invisible_form_view(self):
        self.env.company.country_id = self.country_mx
        arch, view = self.ResPartner._get_view()
        arch_annexed_establishment = arch.xpath("//field[@name='annexed_establishment']")
        self.assertTrue(
            'invisible' in arch_annexed_establishment[0].attrib,
            "El campo 'annexed_establishment' debe estar invisible."
        )
        print("TEST OK")
    
    def test_annexed_establishment_visible_multiple_countries(self):
        """El campo debe permanecer visible si la compañía está en la lista de países permitidos (PE o MX)."""
        countries = [self.country_pe, self.country_mx]
        arch, view = self.ResPartner._tags_invisible_per_country(
            *self.ResPartner._get_view(), 
            tags=['annexed_establishment'], 
            countries=countries
        )
        arch_field = arch.xpath("//field[@name='annexed_establishment']")[0]
        self.assertFalse(
            'invisible' in arch_field.attrib,
            "El campo 'annexed_establishment' no debe estar invisible cuando la compañía está en la lista de países permitidos."
        )
        print("TEST OK")
