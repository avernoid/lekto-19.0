from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAutoManufacturingOrder(TransactionCase):
    """Tests de la creación de la Orden de Manufactura desde un ECO aprobado,
    ligada a la venta como su abastecimiento (cadena MTO)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env.company
        cls.env.user.group_ids += cls.env.ref('mrp_plm.group_plm_user')
        cls.warehouse = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.company.id)], limit=1)

        cls.partner = cls.env['res.partner'].create({'name': 'Cliente MTO'})

        # Tipo de ECO CON auto_create_mo.
        cls.eco_type_auto = cls.env['mrp.eco.type'].create({
            'name': 'Tipo auto MO',
            'auto_create_mo': True,
        })
        # Tipo de ECO SIN auto_create_mo (para el test de gate).
        cls.eco_type_manual = cls.env['mrp.eco.type'].create({
            'name': 'Tipo sin auto MO',
            'auto_create_mo': False,
        })

        # Etapa inicial y etapa disparadora, ligadas a ambos tipos.
        cls.stage_new = cls.env['mrp.eco.stage'].create({
            'name': 'Nuevo',
            'sequence': 1,
            'type_ids': [(6, 0, [cls.eco_type_auto.id, cls.eco_type_manual.id])],
        })
        cls.stage_trigger = cls.env['mrp.eco.stage'].create({
            'name': 'Aprobado',
            'sequence': 10,
            'triggers_mo_creation': True,
            'type_ids': [(6, 0, [cls.eco_type_auto.id, cls.eco_type_manual.id])],
        })

        # Componente para poder completar la BoM.
        cls.component = cls.env['product.product'].create({
            'name': 'Componente',
            'type': 'consu',
            'is_storable': True,
        })

    def _make_category(self, eco_type):
        return self.env['product.category'].create({
            'name': 'Cat ingeniería %s' % eco_type.name,
            'requires_engineering': True,
            'eco_type_id': eco_type.id,
        })

    def _make_custom_product(self, eco_type):
        return self.env['product.product'].create({
            'name': 'Producto a medida',
            'type': 'consu',
            'is_storable': True,
            'categ_id': self._make_category(eco_type).id,
            'list_price': 1000.0,
        })

    def _confirm_order(self, product, qty=3):
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'warehouse_id': self.warehouse.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': qty,
            })],
        })
        order.action_confirm()
        return order

    def _complete_bom(self, eco):
        """Ingeniería añade un componente a la BoM vacía creada por el módulo."""
        self.assertTrue(eco.bom_id, "El ECO debe traer una BoM creada.")
        eco.bom_id.write({
            'bom_line_ids': [(0, 0, {
                'product_id': self.component.id,
                'product_qty': 2.0,
            })],
        })

    # ------------------------------------------------------------------
    def test_mo_created_and_linked_to_sale(self):
        """Al llegar a la etapa disparadora se crea la MO encadenada a la
        entrega de la venta (cadena MTO)."""
        product = self._make_custom_product(self.eco_type_auto)
        order = self._confirm_order(product, qty=3)
        eco = self.env['mrp.eco'].search([('sale_id', '=', order.id)])
        self.assertEqual(len(eco), 1)
        self._complete_bom(eco)

        delivery_moves = order.order_line.move_ids.filtered(
            lambda m: m.state not in ('done', 'cancel'))
        self.assertTrue(delivery_moves, "Debe existir el movimiento de entrega.")

        eco.stage_id = self.stage_trigger

        mo = eco.generated_production_id
        self.assertTrue(mo, "Debe crearse la Orden de Manufactura.")
        self.assertEqual(mo.product_id, product)
        self.assertEqual(mo.origin, order.name)
        # Cadena MTO: el movimiento de producto terminado apunta a la entrega.
        finished = mo.move_finished_ids
        self.assertTrue(finished, "La MO debe tener movimiento de producto terminado.")
        self.assertTrue(
            delivery_moves & finished.move_dest_ids,
            "El finished move debe encadenar a la entrega (move_dest_ids).")
        self.assertTrue(
            finished & delivery_moves.move_orig_ids,
            "La entrega debe quedar abastecida por la MO (move_orig_ids).")

    def test_idempotency_no_duplicate_mo(self):
        """Reentrar a la etapa disparadora no crea una segunda MO."""
        product = self._make_custom_product(self.eco_type_auto)
        order = self._confirm_order(product)
        eco = self.env['mrp.eco'].search([('sale_id', '=', order.id)])
        self._complete_bom(eco)

        eco.stage_id = self.stage_trigger
        mo = eco.generated_production_id
        self.assertTrue(mo)

        mo_count_before = self.env['mrp.production'].search_count(
            [('product_id', '=', product.id)])
        # Reintento del flujo automático (no debe duplicar).
        eco._create_manufacturing_order_for_sale()
        mo_count_after = self.env['mrp.production'].search_count(
            [('product_id', '=', product.id)])
        self.assertEqual(mo_count_before, mo_count_after,
                         "No debe crearse una segunda MO.")
        self.assertEqual(eco.generated_production_id, mo)

    def test_gate_by_eco_type(self):
        """Sin auto_create_mo en el tipo, el cambio de etapa NO crea MO, pero el
        botón manual SÍ."""
        product = self._make_custom_product(self.eco_type_manual)
        order = self._confirm_order(product)
        eco = self.env['mrp.eco'].search([('sale_id', '=', order.id)])
        self._complete_bom(eco)

        eco.stage_id = self.stage_trigger
        self.assertFalse(eco.generated_production_id,
                         "Tipo sin auto_create_mo no debe crear MO al cambiar etapa.")

        # Botón manual: crea la MO ignorando el gate.
        eco.action_create_sale_manufacturing_order()
        self.assertTrue(eco.generated_production_id,
                        "El botón manual debe crear la MO.")

    def test_no_mo_without_usable_bom(self):
        """Sin BoM con componentes, no se crea MO y no se rompe el cambio de
        etapa (flujo automático no bloqueante)."""
        product = self._make_custom_product(self.eco_type_auto)
        order = self._confirm_order(product)
        eco = self.env['mrp.eco'].search([('sale_id', '=', order.id)])
        # BoM vacía (sin completar).
        eco.stage_id = self.stage_trigger
        self.assertFalse(eco.generated_production_id,
                         "Sin BoM usable no debe crearse MO.")

        # Por el botón manual debe avisar con UserError.
        with self.assertRaises(UserError):
            eco.action_create_sale_manufacturing_order()

    def test_manual_button_raises_when_already_created(self):
        """El botón manual avisa si ya existe una MO generada."""
        product = self._make_custom_product(self.eco_type_auto)
        order = self._confirm_order(product)
        eco = self.env['mrp.eco'].search([('sale_id', '=', order.id)])
        self._complete_bom(eco)
        eco.stage_id = self.stage_trigger
        self.assertTrue(eco.generated_production_id)

        with self.assertRaises(UserError):
            eco.action_create_sale_manufacturing_order()
