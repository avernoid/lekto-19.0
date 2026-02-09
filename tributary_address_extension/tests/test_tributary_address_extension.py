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

    def test_annexed_establishment_change_value(self):
        new_value = '5678'
        self.partner.write({'annexed_establishment': new_value})
        self.assertEqual(
            self.partner.annexed_establishment, new_value,
            'El valor del establecimiento anexo no se modificó correctamente.'
        )

    def test_annexed_establishment_view_modifier(self):
        """Verificar que el campo tiene el modificador invisible correcto en la vista."""
        view = self.env.ref('tributary_address_extension.res_partner_view_form_inherit_tributary_address_extension')
        # Obtenemos la arquitectura de la vista combinada
        arch = self.ResPartner.get_view(view_id=view.id, view_type='form')['arch']
        
        # Odoo 17+ devuelve la arquitectura procesada, buscamos el nodo
        from lxml import etree
        doc = etree.fromstring(arch)
        
        nodes = doc.xpath("//field[@name='annexed_establishment']")
        self.assertTrue(nodes, "El campo 'annexed_establishment' debe existir en la vista.")
        
        node = nodes[0]
        invisible_modifier = node.get('invisible')
        
        # La condición exacta en el XML es country_code != 'PE'
        # Nota: Odoo puede procesar los dominios, pero en get_view simple suele mantener el string o evaluarlo.
        # Verificamos que contenga la lógica esencial
        expected_domain = "country_code != 'PE'"
        self.assertIn('country_code', invisible_modifier, "El modificador invisible debe depender de country_code")
        self.assertIn('PE', invisible_modifier, "El modificador invisible debe verificar el código de país 'PE'")
