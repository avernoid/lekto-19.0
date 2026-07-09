from odoo.tests import Form, TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestQualityProfile(TransactionCase):
    """Perfiles de calidad por pedido: filtran los quality.check creados en las
    operaciones de entrega y de manufactura de la venta."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.warehouse = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.company.id)], limit=1)
        cls.out_type = cls.warehouse.out_type_id
        cls.manu_type = cls.warehouse.manu_type_id
        cls.partner = cls.env['res.partner'].create({'name': 'Cliente QC'})
        cls.team = cls.env['quality.alert.team'].create({'name': 'QC Team'})
        cls.passfail = cls.env.ref('quality_control.test_type_passfail')

        cls.product = cls.env['product.product'].create({
            'name': 'Producto QC',
            'type': 'consu',
            'is_storable': True,
        })
        cls.other_product = cls.env['product.product'].create({
            'name': 'Otro producto',
            'type': 'consu',
            'is_storable': True,
        })

        # Puntos de calidad de ENTREGA (out_type), sin restricción de producto.
        cls.p_out_product = cls._make_point(cls, cls.out_type, 'product')
        cls.p_out_operation = cls._make_point(cls, cls.out_type, 'operation')
        # Punto de entrega restringido a otro producto (no casa nativamente).
        cls.p_out_other = cls._make_point(
            cls, cls.out_type, 'product', product=cls.other_product)

        # Puntos de calidad de MANUFACTURA (manu_type).
        cls.p_mo_product = cls._make_point(cls, cls.manu_type, 'product')
        cls.p_mo_operation = cls._make_point(cls, cls.manu_type, 'operation')
        # Punto de manufactura restringido a otro producto (no casa nativamente).
        cls.p_mo_other = cls._make_point(
            cls, cls.manu_type, 'product', product=cls.other_product)

    def _make_point(self, picking_type, measure_on, product=None):
        vals = {
            'title': 'QP %s %s' % (picking_type.id, measure_on),
            'picking_type_ids': [(6, 0, [picking_type.id])],
            'test_type_id': self.passfail.id,
            'team_id': self.team.id,
            'measure_on': measure_on,
        }
        if product is not None:
            vals['product_ids'] = [(6, 0, [product.id])]
        return self.env['quality.point'].create(vals)

    def _make_order(self, delivery_profile=None, manufacturing_profile=None):
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'warehouse_id': self.warehouse.id,
            'delivery_quality_profile_id': delivery_profile.id if delivery_profile else False,
            'manufacturing_quality_profile_id': manufacturing_profile.id if manufacturing_profile else False,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 2,
            })],
        })
        return order

    def _profile(self, points, enforcement='restrict'):
        return self.env['quality.profile'].create({
            'name': 'Profile %s' % enforcement,
            'enforcement': enforcement,
            'point_ids': [(6, 0, points.ids)],
        })

    def _delivery_checks(self, order):
        return order.picking_ids.check_ids

    # ------------------------------------------------------------------
    # Entrega
    # ------------------------------------------------------------------
    def test_delivery_restrict_subset(self):
        """restrict: solo se conservan los checks de los puntos del perfil."""
        profile = self._profile(self.p_out_product)
        order = self._make_order(delivery_profile=profile)
        order.action_confirm()

        points = self._delivery_checks(order).point_id
        self.assertIn(self.p_out_product, points, "El punto del perfil debe estar.")
        self.assertNotIn(self.p_out_operation, points,
                         "El punto NO incluido en el perfil debe podarse.")

    def test_delivery_no_profile_is_native(self):
        """Sin perfil: comportamiento nativo, ambos puntos generan check."""
        order = self._make_order()
        order.action_confirm()

        points = self._delivery_checks(order).point_id
        self.assertIn(self.p_out_product, points)
        self.assertIn(self.p_out_operation, points)

    def test_delivery_restrict_empty_means_none(self):
        """restrict con lista vacía: ningún check de operación/producto."""
        empty_profile = self._profile(self.env['quality.point'])
        order = self._make_order(delivery_profile=empty_profile)
        order.action_confirm()

        checks = self._delivery_checks(order).filtered(
            lambda c: c.measure_on in ('operation', 'product'))
        self.assertFalse(checks, "restrict vacío no debe dejar checks.")

    def test_delivery_additive_forces_extra_point(self):
        """additive: fuerza un punto que no casa nativamente (otro producto)."""
        profile = self._profile(
            self.p_out_product | self.p_out_other, enforcement='additive')
        order = self._make_order(delivery_profile=profile)
        order.action_confirm()

        points = self._delivery_checks(order).point_id
        # Nativos + forzado.
        self.assertIn(self.p_out_product, points)
        self.assertIn(self.p_out_operation, points, "Los nativos se conservan.")
        self.assertIn(self.p_out_other, points, "El punto del perfil se fuerza.")

    # ------------------------------------------------------------------
    # Manufactura
    # ------------------------------------------------------------------
    def _make_confirmed_mo(self, order, manufacturing_profile=None):
        if manufacturing_profile is not None:
            order.manufacturing_quality_profile_id = manufacturing_profile
        self.assertTrue(order.stock_reference_ids,
                        "La venta confirmada debe tener stock.reference.")
        component = self.env['product.product'].create({
            'name': 'Componente QC', 'type': 'consu', 'is_storable': True})
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [(0, 0, {'product_id': component.id, 'product_qty': 1})],
        })
        mo = self.env['mrp.production'].create({
            'product_id': self.product.id,
            'product_qty': 1.0,
            'bom_id': bom.id,
            'reference_ids': [(6, 0, order.stock_reference_ids.ids)],
        })
        mo.action_confirm()
        return mo

    def test_mo_restrict_subset(self):
        """restrict en manufactura: solo el punto del perfil sobrevive."""
        order = self._make_order()
        order.action_confirm()
        profile = self._profile(self.p_mo_product)
        mo = self._make_confirmed_mo(order, manufacturing_profile=profile)

        points = mo.check_ids.point_id
        self.assertIn(self.p_mo_product, points)
        self.assertNotIn(self.p_mo_operation, points)

    def test_mo_no_profile_is_native(self):
        """Sin perfil de manufactura: nativo, ambos puntos generan check."""
        order = self._make_order()
        order.action_confirm()
        mo = self._make_confirmed_mo(order)

        points = mo.check_ids.point_id
        self.assertIn(self.p_mo_product, points)
        self.assertIn(self.p_mo_operation, points)

    def test_mo_restrict_empty_means_none(self):
        """restrict vacío en manufactura: ningún check de operación/producto."""
        order = self._make_order()
        order.action_confirm()
        empty_profile = self._profile(self.env['quality.point'])
        mo = self._make_confirmed_mo(order, manufacturing_profile=empty_profile)

        checks = mo.check_ids.filtered(
            lambda c: c.measure_on in ('operation', 'product'))
        self.assertFalse(checks, "restrict vacío no debe dejar checks en la MO.")

    def test_mo_additive_forces_extra_point(self):
        """additive en manufactura: fuerza un punto que no casa nativamente."""
        order = self._make_order()
        order.action_confirm()
        profile = self._profile(self.p_mo_other, enforcement='additive')
        mo = self._make_confirmed_mo(order, manufacturing_profile=profile)

        points = mo.check_ids.point_id
        self.assertIn(self.p_mo_product, points, "Los nativos se conservan.")
        self.assertIn(self.p_mo_operation, points, "Los nativos se conservan.")
        self.assertIn(self.p_mo_other, points, "El punto del perfil se fuerza.")

    # ------------------------------------------------------------------
    # Independencia entre perfil de entrega y de manufactura
    # ------------------------------------------------------------------
    def test_delivery_profile_does_not_affect_mo(self):
        """El perfil de ENTREGA no debe alterar los checks de la MO."""
        delivery_profile = self._profile(self.p_out_product)  # restrict entrega
        order = self._make_order(delivery_profile=delivery_profile)
        order.action_confirm()
        # Sin perfil de manufactura → la MO debe quedar nativa.
        mo = self._make_confirmed_mo(order)

        points = mo.check_ids.point_id
        self.assertIn(self.p_mo_product, points,
                      "La MO debe seguir nativa pese al perfil de entrega.")
        self.assertIn(self.p_mo_operation, points)

    def test_mo_profile_does_not_affect_delivery(self):
        """El perfil de MANUFACTURA no debe alterar los checks de entrega."""
        mo_profile = self._profile(self.p_mo_product)  # restrict manufactura
        order = self._make_order(manufacturing_profile=mo_profile)
        order.action_confirm()

        points = self._delivery_checks(order).point_id
        self.assertIn(self.p_out_product, points,
                      "La entrega debe seguir nativa pese al perfil de MO.")
        self.assertIn(self.p_out_operation, points)

    def test_additive_respects_picking_type(self):
        """additive no fuerza un punto de MANUFACTURA sobre una ENTREGA."""
        # Perfil de entrega additive que incluye un punto de manu_type.
        profile = self._profile(self.p_mo_product, enforcement='additive')
        order = self._make_order(delivery_profile=profile)
        order.action_confirm()

        points = self._delivery_checks(order).point_id
        self.assertNotIn(self.p_mo_product, points,
                         "Un punto de manufactura no debe forzarse en la entrega.")
        self.assertIn(self.p_out_product, points, "Los nativos de entrega siguen.")

    def test_additive_does_not_duplicate_native_point(self):
        """additive no duplica un punto que ya existe de forma nativa."""
        profile = self._profile(self.p_out_product, enforcement='additive')
        order = self._make_order(delivery_profile=profile)
        order.action_confirm()

        matching = self._delivery_checks(order).filtered(
            lambda c: c.point_id == self.p_out_product)
        self.assertEqual(len(matching), 1,
                         "El punto nativo no debe duplicarse en modo aditivo.")

    # ------------------------------------------------------------------
    # Garantías de seguridad (no romper / no destruir)
    # ------------------------------------------------------------------
    def test_move_line_checks_are_not_filtered(self):
        """Los checks 'move_line' (por cantidad) quedan fuera del filtro."""
        profile = self._profile(self.p_out_product)  # restrict, sin ml_point
        order = self._make_order(delivery_profile=profile)
        order.action_confirm()
        picking = order.picking_ids

        ml_point = self._make_point(self.out_type, 'move_line')
        ml_check = self.env['quality.check'].create({
            'point_id': ml_point.id,
            'measure_on': 'move_line',
            'team_id': self.team.id,
            'product_id': self.product.id,
            'picking_id': picking.id,
            'company_id': self.company.id,
        })
        # Re-disparar el filtro; NO debe tocar el check move_line.
        picking.move_ids._create_quality_checks()
        self.assertTrue(ml_check.exists(),
                        "El filtro no debe eliminar checks de tipo move_line.")

    def test_restrict_preserves_completed_checks(self):
        """restrict solo poda checks en estado 'none'; respeta los completados."""
        order = self._make_order()  # sin perfil → nativos
        order.action_confirm()
        picking = order.picking_ids
        done_check = picking.check_ids.filtered(
            lambda c: c.point_id == self.p_out_operation)
        self.assertTrue(done_check)
        done_check.quality_state = 'pass'  # se marca como realizado

        # Ahora se asigna un perfil que EXCLUYE ese punto y se re-filtra.
        order.delivery_quality_profile_id = self._profile(self.p_out_product)
        picking.move_ids._create_quality_checks()
        self.assertTrue(done_check.exists(),
                        "Un check ya realizado no debe eliminarse por el perfil.")

    def test_regenerate_quality_checks_action(self):
        """La acción de regenerar aplica el perfil actualizado a lo pendiente."""
        order = self._make_order(delivery_profile=self._profile(self.p_out_product))
        order.action_confirm()
        points = self._delivery_checks(order).point_id
        self.assertIn(self.p_out_product, points)
        self.assertNotIn(self.p_out_operation, points)

        # Cambiar a un perfil distinto y regenerar.
        order.delivery_quality_profile_id = self._profile(self.p_out_operation)
        order.action_regenerate_quality_checks()

        points = self._delivery_checks(order).filtered(
            lambda c: c.measure_on in ('operation', 'product')).point_id
        self.assertIn(self.p_out_operation, points, "Debe reflejar el nuevo perfil.")
        self.assertNotIn(self.p_out_product, points, "El punto anterior se retira.")

    # ------------------------------------------------------------------
    # Autocompletado cruzado de perfiles (onchange, solo formulario)
    # ------------------------------------------------------------------
    def _order_form(self):
        form = Form(self.env['sale.order'])
        form.partner_id = self.partner
        return form

    def test_onchange_delivery_fills_empty_manufacturing(self):
        """Fijar entrega autocompleta manufactura si estaba vacío."""
        profile = self._profile(self.p_out_product)
        form = self._order_form()
        form.delivery_quality_profile_id = profile
        self.assertEqual(form.manufacturing_quality_profile_id, profile)

    def test_onchange_manufacturing_fills_empty_delivery(self):
        """Simétrico: fijar manufactura autocompleta entrega si estaba vacío."""
        profile = self._profile(self.p_mo_product)
        form = self._order_form()
        form.manufacturing_quality_profile_id = profile
        self.assertEqual(form.delivery_quality_profile_id, profile)

    def test_onchange_does_not_overwrite_existing(self):
        """No pisa un valor ya puesto: los campos pueden divergir."""
        p_mo = self._profile(self.p_mo_product)
        p_del = self._profile(self.p_out_product)
        form = self._order_form()
        form.manufacturing_quality_profile_id = p_mo  # autocompleta entrega=p_mo
        form.delivery_quality_profile_id = p_del       # el usuario la cambia
        # Entrega=p_del pero manufactura NO debe cambiar (ya tenía valor).
        self.assertEqual(form.manufacturing_quality_profile_id, p_mo)
        self.assertEqual(form.delivery_quality_profile_id, p_del)

    def test_onchange_clear_after_autofill_stays_empty(self):
        """Si se limpia el que se autocompletó, queda vacío (no se re-rellena)."""
        profile = self._profile(self.p_out_product)
        form = self._order_form()
        form.delivery_quality_profile_id = profile     # autocompleta manufactura
        self.assertEqual(form.manufacturing_quality_profile_id, profile)
        form.manufacturing_quality_profile_id = self.env['quality.profile']
        self.assertFalse(form.manufacturing_quality_profile_id)

    # ------------------------------------------------------------------
    # Modelo + data demo
    # ------------------------------------------------------------------
    def test_point_count_compute(self):
        profile = self._profile(self.p_out_product | self.p_out_operation)
        self.assertEqual(profile.point_count, 2)

    def test_learning_demo_runs_and_is_idempotent(self):
        """El generador de data demo corre sin error y es idempotente."""
        Profile = self.env['quality.profile']
        demo_names = ['Estándar', 'Premium', 'Radiografía (+)', 'Sin Control']
        Profile._load_learning_demo()
        demo_profiles = Profile.search([('name', 'in', demo_names)])
        self.assertEqual(len(demo_profiles), 4,
                         "Deben crearse los 4 perfiles demo.")
        # Narrativa publicada en el chatter de los perfiles.
        self.assertTrue(
            self.env['mail.message'].search_count([('model', '=', 'quality.profile')]),
            "El generador debe publicar narrativa en el chatter.")
        # Segunda llamada: no duplica.
        Profile._load_learning_demo()
        self.assertEqual(
            len(Profile.search([('name', 'in', demo_names)])), 4,
            "El generador demo debe ser idempotente.")
