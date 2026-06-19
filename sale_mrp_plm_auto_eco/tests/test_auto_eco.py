from odoo.addons.sale.tests.common import SaleCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAutoEcoCreation(SaleCommon):
    """Tests para la creación automática de ECOs de PLM al confirmar SO."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Agregar grupo PLM al usuario de test para poder crear ECOs.
        cls.env.user.group_ids += cls.env.ref('mrp_plm.group_plm_user')

        # Tipo de ECO para las pruebas.
        cls.eco_type = cls.env['mrp.eco.type'].create({
            'name': 'Test ECO Type',
        })

        # Stage vinculada al tipo (simula "Nuevo", la primera por sequence).
        cls.eco_stage = cls.env['mrp.eco.stage'].create({
            'name': 'Nuevo',
            'sequence': 1,
            'type_ids': [(4, cls.eco_type.id)],
        })

        # Segunda stage para verificar que se asigna la primera.
        cls.eco_stage_2 = cls.env['mrp.eco.stage'].create({
            'name': 'En progreso',
            'sequence': 10,
            'type_ids': [(4, cls.eco_type.id)],
        })

        # Categoría que requiere ingeniería (con eco_type_id configurado).
        cls.categ_engineering = cls.env['product.category'].create({
            'name': 'Test - Requiere Ingeniería',
            'requires_engineering': True,
            'eco_type_id': cls.eco_type.id,
        })

        # Categoría normal (sin ingeniería).
        cls.categ_normal = cls.env['product.category'].create({
            'name': 'Test - Normal',
            'requires_engineering': False,
        })

        # Producto almacenable a medida (elegible).
        cls.product_custom = cls.env['product.product'].create({
            'name': 'Producto a medida test',
            'type': 'consu',
            'is_storable': True,
            'categ_id': cls.categ_engineering.id,
            'list_price': 1000.0,
        })

        # Producto almacenable normal (NO elegible: categoría sin ingeniería).
        cls.product_standard = cls.env['product.product'].create({
            'name': 'Producto estándar test',
            'type': 'consu',
            'is_storable': True,
            'categ_id': cls.categ_normal.id,
            'list_price': 50.0,
        })

        # Producto servicio en categoría ingeniería (NO elegible: no almacenable).
        cls.product_service = cls.env['product.product'].create({
            'name': 'Servicio ingeniería test',
            'type': 'service',
            'categ_id': cls.categ_engineering.id,
            'list_price': 200.0,
        })

        # Producto con BOM existente (NO elegible: ya tiene BOM).
        cls.product_with_bom = cls.env['product.product'].create({
            'name': 'Producto con BOM test',
            'type': 'consu',
            'is_storable': True,
            'categ_id': cls.categ_engineering.id,
            'list_price': 800.0,
        })
        cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.product_with_bom.product_tmpl_id.id,
            'product_qty': 1.0,
        })

    def _create_order_with_product(self, product, qty=1):
        """Helper para crear una SO con una línea del producto dado."""
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': qty,
            })],
        })
        return order

    # --- Tests de creación correcta ---

    def test_eco_created_on_confirm_with_bom(self):
        """Un ECO y su BOM se crean al confirmar SO con producto elegible."""
        order = self._create_order_with_product(self.product_custom)
        order.action_confirm()

        eco = self.env['mrp.eco'].search([
            ('sale_id', '=', order.id),
            ('product_tmpl_id', '=', self.product_custom.product_tmpl_id.id),
        ])
        self.assertEqual(len(eco), 1, "Debe crearse exactamente un ECO.")
        self.assertEqual(eco.type, 'bom', "El ECO debe ser de tipo 'bom'.")
        self.assertEqual(eco.type_id, self.eco_type,
                         "El ECO debe usar el tipo configurado en la categoría.")
        self.assertEqual(eco.sale_id, order,
                         "El ECO debe estar vinculado a la SO.")
        # Verificar que se creó la BOM y está vinculada al ECO.
        self.assertTrue(eco.bom_id, "El ECO debe tener una BOM asociada.")
        self.assertEqual(eco.bom_id.product_tmpl_id,
                         self.product_custom.product_tmpl_id,
                         "La BOM debe estar asociada al producto correcto.")

    def test_eco_has_first_stage(self):
        """El ECO se crea con el primer stage (por sequence) del tipo de ECO."""
        order = self._create_order_with_product(self.product_custom)
        order.action_confirm()

        eco = self.env['mrp.eco'].search([('sale_id', '=', order.id)])
        self.assertEqual(eco.stage_id, self.eco_stage,
                         "El ECO debe tener asignado el primer stage 'Nuevo'.")

    def test_eco_per_unique_product(self):
        """Se crea un ECO (con BOM) por cada product.template único elegible."""
        product_custom_2 = self.env['product.product'].create({
            'name': 'Otro producto a medida',
            'type': 'consu',
            'is_storable': True,
            'categ_id': self.categ_engineering.id,
            'list_price': 2000.0,
        })
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                (0, 0, {'product_id': self.product_custom.id, 'product_uom_qty': 1}),
                (0, 0, {'product_id': product_custom_2.id, 'product_uom_qty': 2}),
                (0, 0, {'product_id': self.product_standard.id, 'product_uom_qty': 5}),
            ],
        })
        order.action_confirm()

        ecos = self.env['mrp.eco'].search([('sale_id', '=', order.id)])
        self.assertEqual(len(ecos), 2, "Deben crearse 2 ECOs (uno por producto a medida).")
        for eco in ecos:
            self.assertTrue(eco.bom_id, "Cada ECO debe tener una BOM asociada.")

    def test_duplicate_lines_single_eco(self):
        """Múltiples líneas del mismo producto crean solo un ECO y una BOM."""
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                (0, 0, {'product_id': self.product_custom.id, 'product_uom_qty': 3}),
                (0, 0, {'product_id': self.product_custom.id, 'product_uom_qty': 7}),
            ],
        })
        order.action_confirm()

        ecos = self.env['mrp.eco'].search([
            ('sale_id', '=', order.id),
            ('product_tmpl_id', '=', self.product_custom.product_tmpl_id.id),
        ])
        self.assertEqual(len(ecos), 1, "Líneas duplicadas deben generar solo un ECO.")

    # --- Tests de NO creación (condiciones no cumplidas) ---

    def test_no_eco_for_standard_category(self):
        """No se crea ECO si la categoría no requiere ingeniería."""
        order = self._create_order_with_product(self.product_standard)
        order.action_confirm()

        ecos = self.env['mrp.eco'].search([('sale_id', '=', order.id)])
        self.assertFalse(ecos, "No debe crearse ECO para categoría sin ingeniería.")

    def test_no_eco_for_service(self):
        """No se crea ECO para productos de tipo servicio."""
        order = self._create_order_with_product(self.product_service)
        order.action_confirm()

        ecos = self.env['mrp.eco'].search([('sale_id', '=', order.id)])
        self.assertFalse(ecos, "No debe crearse ECO para servicios.")

    def test_no_eco_for_product_with_bom(self):
        """No se crea ECO si el producto ya tiene una BOM."""
        order = self._create_order_with_product(self.product_with_bom)
        order.action_confirm()

        ecos = self.env['mrp.eco'].search([('sale_id', '=', order.id)])
        self.assertFalse(ecos, "No debe crearse ECO para producto con BOM existente.")

    # --- Tests de idempotencia ---

    def test_idempotency_no_duplicate_eco(self):
        """Reconfirmar la misma SO no crea ECOs ni BOMs duplicados."""
        order = self._create_order_with_product(self.product_custom)
        order.action_confirm()

        ecos_before = self.env['mrp.eco'].search([('sale_id', '=', order.id)])
        self.assertEqual(len(ecos_before), 1)

        # Cancelar → draft → reconfirmar (flujo real de reconfirmación).
        order._action_cancel()
        order.action_draft()
        order.action_confirm()

        ecos_after = self.env['mrp.eco'].search([('sale_id', '=', order.id)])
        self.assertEqual(
            len(ecos_after), 1,
            "Reconfirmar la SO no debe crear ECOs duplicados.",
        )

    # --- Tests de smart button y relación ---

    def test_eco_count(self):
        """El conteo de ECOs en la SO refleja los ECOs creados."""
        order = self._create_order_with_product(self.product_custom)
        order.action_confirm()

        self.assertEqual(order.eco_count, 1, "eco_count debe ser 1.")

    def test_smart_button_action_single_eco(self):
        """El smart button abre el formulario si hay un solo ECO."""
        order = self._create_order_with_product(self.product_custom)
        order.action_confirm()

        action = order.action_view_ecos()
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['res_id'], order.eco_ids.id)

    def test_smart_button_action_multiple_ecos(self):
        """El smart button abre la lista si hay múltiples ECOs."""
        product_custom_2 = self.env['product.product'].create({
            'name': 'Otro producto a medida 2',
            'type': 'consu',
            'is_storable': True,
            'categ_id': self.categ_engineering.id,
            'list_price': 2000.0,
        })
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                (0, 0, {'product_id': self.product_custom.id, 'product_uom_qty': 1}),
                (0, 0, {'product_id': product_custom_2.id, 'product_uom_qty': 1}),
            ],
        })
        order.action_confirm()

        action = order.action_view_ecos()
        self.assertEqual(action['view_mode'], 'list,form')
        self.assertEqual(order.eco_count, 2)

    # --- Test de usuario sin permiso PLM ---

    def test_eco_created_by_user_without_plm(self):
        """Un vendedor SIN permiso de PLM confirma la SO y el ECO se crea igual.

        La creación del ECO/BOM corre con sudo(), por lo que la falta de
        permisos de PLM del usuario que confirma no debe impedirla.
        """
        sales_user = self.env['res.users'].create({
            'name': 'Vendedor sin PLM',
            'login': 'vendedor_sin_plm',
            'email': 'vendedor_sin_plm@test.com',
            'group_ids': [(6, 0, [
                self.env.ref('sales_team.group_sale_salesman').id,
            ])],
        })
        # Sanity check: el usuario NO tiene permiso de PLM.
        self.assertFalse(
            sales_user.has_group('mrp_plm.group_plm_user'),
            "El usuario de prueba no debe tener permiso de PLM.",
        )

        # El vendedor debe ser dueño de la orden para poder confirmarla
        # (regla de registro de ventas: solo edita sus propias órdenes).
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'user_id': sales_user.id,
            'order_line': [(0, 0, {
                'product_id': self.product_custom.id,
                'product_uom_qty': 1,
            })],
        })
        order.with_user(sales_user).action_confirm()

        eco = self.env['mrp.eco'].search([('sale_id', '=', order.id)])
        self.assertEqual(
            len(eco), 1,
            "El ECO debe crearse aunque el usuario no tenga permiso de PLM.",
        )
        self.assertTrue(eco.bom_id, "El ECO debe tener su BOM creada.")
        # El conteo de ECOs debe poder leerse como el usuario sin PLM.
        self.assertEqual(
            order.with_user(sales_user).eco_count, 1,
            "eco_count debe poder computarse para un usuario sin PLM.",
        )

    # --- Test de confirmación no se rompe ---

    def test_confirmation_succeeds_even_with_eligible_products(self):
        """La confirmación de la SO debe completarse exitosamente."""
        order = self._create_order_with_product(self.product_custom)
        result = order.action_confirm()
        self.assertTrue(result, "action_confirm debe retornar True.")
        self.assertEqual(order.state, 'sale', "La SO debe quedar en estado 'sale'.")
