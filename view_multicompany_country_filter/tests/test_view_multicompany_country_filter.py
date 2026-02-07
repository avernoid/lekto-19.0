from lxml import etree
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestViewMulticompanyCountryFilter(TransactionCase):

    @classmethod
    def setUpClass(cls):
        """
        Configuración inicial de la clase de pruebas.
        """
        super().setUpClass()
        # Usamos el mixin directamente para probar la lógica estática
        cls.mixin_model = cls.env['view.multicompany.country.filter.mixin']
        cls.ResPartner = cls.env['res.partner']
        cls.country_pe = cls.env.ref('base.pe')
        cls.country_mx = cls.env.ref('base.mx')

    def setUp(self):
        """
        Configuración adicional antes de cada prueba.
        """
        super().setUp()
        self.env.company.country_id = self.country_pe

    def _create_view_arch(self, tag_names, view_type='form'):
        """
        Crea un elemento XML de vista con las etiquetas especificadas.
        """    
        arch = etree.Element(view_type)
        for name in tag_names:
            if isinstance(name, tuple):
                tag = etree.SubElement(arch, name[0])
                tag.set('name', name[1])
            else:
                field = etree.SubElement(arch, 'field')
                field.set('name', name)
        return arch

    def _check_tags_visibility_view_arch(self, country, tags, check_visibility, view_type='form'):
        """
        Verifica la visibilidad de las etiquetas en un elemento XML de vista en base a la configuración del país.
        """
        
        # Construimos una vista con los elementos necesarios
        field_1 = 'field_1'
        group_1 = 'group_1'
        
        # Preparamos tags para crear la estructura XML
        xml_tags = [field_1]
        if view_type == 'form':
             xml_tags.append(('group', group_1))
             
        arch = self._create_view_arch(xml_tags, view_type=view_type)
        
        countries = country if isinstance(country, list) else [country]

        # LLAMADA ACTUALIZADA: Usamos el modelo mixin directamente
        arch, view = self.mixin_model._tags_invisible_per_country(arch, None, view_type, tags, countries)

        arch_field_1 = arch.xpath(f"//field[@name='{field_1}']")
        
        # Determinar atributo esperado
        invisible_attr = 'invisible'
        if view_type in ('tree', 'list'):
             invisible_attr = 'column_invisible'

        if check_visibility:
            self.assertFalse(invisible_attr in arch_field_1[0].attrib, f"El campo '{field_1}' no debe estar invisible.")
            if view_type == 'form':
                arch_group_1 = arch.xpath(f"//group[@name='{group_1}']")
                self.assertFalse('invisible' in arch_group_1[0].attrib, f"El grupo '{group_1}' no debe estar invisible.")
        else:
            self.assertTrue(invisible_attr in arch_field_1[0].attrib, f"El campo '{field_1}' debe estar invisible.")
            if view_type == 'form':
                arch_group_1 = arch.xpath(f"//group[@name='{group_1}']")
                self.assertTrue('invisible' in arch_group_1[0].attrib, f"El grupo '{group_1}' debe estar invisible.")

    def test_tags_visible_when_country_matches(self):
        self._check_tags_visibility_view_arch(
            country=self.country_pe, 
            tags=['field_1', ('group', 'group_1')], 
            check_visibility=True
        )

    def test_tags_invisible_when_country_does_not_match(self):
        self._check_tags_visibility_view_arch(
            country=self.country_mx, 
            tags=['field_1', ('group', 'group_1')], 
            check_visibility=False
        )
        
    def test_tags_visible_with_empty_tags_and_countries_lists(self):
        self._check_tags_visibility_view_arch(
            country=[], 
            tags=[], 
            check_visibility=True
        )

    def test_tags_visible_with_multiple_countries(self):
        self._check_tags_visibility_view_arch(
            country=[self.country_mx, self.country_pe], 
            tags=['field_1', ('group', 'group_1')], 
            check_visibility=True
        )

    def test_tree_view_column_invisible(self):
        self._check_tags_visibility_view_arch(
            country=self.country_mx, 
            tags=['field_1'], 
            check_visibility=False,
            view_type='tree'
        )

    def test_list_view_column_invisible(self):
        self._check_tags_visibility_view_arch(
            country=self.country_mx, 
            tags=['field_1'], 
            check_visibility=False,
            view_type='list'
        )

    def test_view_cache_key_default(self):
        """
        Prueba que la clave de caché POR DEFECTO no incluye la compañía (ya que ResPartner no tiene el Mixin).
        Esto confirma que hemos eliminado el 'Field Leaking' global.
        """
        # ResPartner no hereda del mixin, asi que debe usar la logica base de Odoo
        key = self.ResPartner._get_view_cache_key(view_id=1, view_type='form')
        
        # Al no tener el mixin, la clave NO debe cambiar respecto al super.
        # Por ende, NO debe tener la compañía al final.
        if len(key) > 0 and key[-1] == self.env.company:
             self.fail("ResPartner no debería tener la compañía en la clave de caché sin heredar el Mixin")
