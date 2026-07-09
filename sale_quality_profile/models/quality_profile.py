from markupsafe import Markup

from odoo import api, fields, models


class QualityProfile(models.Model):
    """Perfil de calidad reutilizable: agrupa quality.point en un 'tier'
    (Básico/Estándar/Premium...) que se elige en el pedido de venta para
    decidir qué controles aplican a sus operaciones de manufactura y entrega."""

    _name = 'quality.profile'
    _description = 'Quality Control Profile'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char('Name', required=True)
    active = fields.Boolean('Active', default=True)
    company_id = fields.Many2one(
        'res.company', 'Company', default=lambda self: self.env.company)
    point_ids = fields.Many2many(
        'quality.point', string='Control Points',
        help="Quality control points that make up this profile. When the "
             "profile is assigned to a sale order, only these points (in "
             "'restrict' mode) or these plus the native ones (in 'additive' "
             "mode) will generate quality checks on the order's operations.")
    enforcement = fields.Selection(
        selection=[
            ('restrict', 'Only these control points'),
            ('additive', 'Native control points + these'),
        ],
        string='Behavior', default='restrict', required=True,
        help="Restrict: on the order's operations only this profile's points "
             "generate checks (whitelist over what natively matches). An empty "
             "point list therefore means no checks.\n"
             "Additive: the native matching points plus this profile's points.")
    point_count = fields.Integer('# Points', compute='_compute_point_count')

    def _compute_point_count(self):
        for profile in self:
            profile.point_count = len(profile.point_ids)

    # ==================================================================
    # Demo "learning book"
    # ------------------------------------------------------------------
    # Generado exclusivamente desde demo/quality_profile_demo.xml. Crea un
    # conjunto de registros interrelacionados y escribe en el chatter de cada
    # uno una explicación didáctica (con enlaces cruzados) para entender el
    # módulo, su configuración y por qué se generó cada control de calidad.
    # ==================================================================
    @staticmethod
    def _demo_post(record, body):
        record.message_post(body=body, subtype_xmlid='mail.mt_comment')

    @staticmethod
    def _demo_links(records, sep=", "):
        return Markup(sep).join(r._get_html_link() for r in records) or Markup("—")

    @api.model
    def _load_learning_demo(self):
        """Punto de entrada de la data demo didáctica. Idempotente."""
        # Guard de idempotencia anclado al partner demo (conserva el sufijo
        # "(Demo)"), no a un nombre de perfil: los perfiles ahora son cortos
        # ('Estándar', 'Premium', ...) y un cliente podría tener uno igual.
        if self.env['res.partner'].search_count(
                [('name', '=', 'ACME Aeroespacial (Demo)')]):
            return  # ya cargada (p. ej. en un -u posterior)

        post = self._demo_post
        links = self._demo_links

        company = self.env.company
        warehouse = self.env['stock.warehouse'].search(
            [('company_id', '=', company.id)], limit=1)
        out_type = warehouse.out_type_id
        manu_type = warehouse.manu_type_id
        passfail = self.env.ref('quality_control.test_type_passfail')

        partner = self.env['res.partner'].create({'name': 'ACME Aeroespacial (Demo)'})
        team = self.env['quality.alert.team'].create({'name': 'Equipo de Calidad (Demo)'})

        # --- Productos + BoM ------------------------------------------------
        Product = self.env['product.product']
        widget = Product.create({
            'name': 'Actuador Hidráulico (Demo)',
            'type': 'consu', 'is_storable': True, 'list_price': 1500.0})
        component = Product.create({
            'name': 'Sello Hidráulico (Demo)',
            'type': 'consu', 'is_storable': True})
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': widget.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [(0, 0, {'product_id': component.id, 'product_qty': 2.0})],
        })

        # --- Puntos de control (quality.point) ------------------------------
        def make_point(title, picking_type, measure_on, product=None):
            vals = {
                'title': title,
                'picking_type_ids': [(6, 0, picking_type.ids)],
                'test_type_id': passfail.id,
                'team_id': team.id,
                'measure_on': measure_on,
            }
            if product is not None:
                vals['product_ids'] = [(6, 0, product.ids)]
            return self.env['quality.point'].create(vals)

        qp_del_dim = make_point('Verificación de dimensiones', out_type, 'product')
        qp_del_visual = make_point('Inspección visual de empaque', out_type, 'operation')
        qp_del_seal = make_point('Certificado de garantía Premium', out_type, 'product')
        qp_mo_torque = make_point('Control de torque de ensamble', manu_type, 'product')
        qp_mo_first = make_point('Validación de primera pieza', manu_type, 'operation')
        # Punto restringido a un producto que NO se vende: no casa nativamente
        # en la entrega del actuador; sirve para ilustrar el modo 'aditivo'.
        qp_xray = make_point('Radiografía industrial (especial)', out_type, 'product',
                             product=component)

        delivery_points = qp_del_dim | qp_del_visual | qp_del_seal
        mo_points = qp_mo_torque | qp_mo_first

        # --- Perfiles (quality.profile) -------------------------------------
        prof_estandar = self.create({
            'name': 'Estándar', 'enforcement': 'restrict',
            'point_ids': [(6, 0, (qp_del_dim | qp_del_visual | qp_mo_torque).ids)]})
        prof_premium = self.create({
            'name': 'Premium', 'enforcement': 'restrict',
            'point_ids': [(6, 0, (qp_del_dim | qp_del_visual | qp_del_seal
                                  | qp_mo_torque | qp_mo_first).ids)]})
        prof_ninguno = self.create({
            'name': 'Sin Control', 'enforcement': 'restrict'})
        prof_aditivo = self.create({
            'name': 'Radiografía (+)', 'enforcement': 'additive',
            'point_ids': [(6, 0, qp_xray.ids)]})

        # --- Pedidos de venta (un escenario cada uno) -----------------------
        def make_order(label, delivery=None, mfg=None):
            return self.env['sale.order'].create({
                'partner_id': partner.id,
                'warehouse_id': warehouse.id,
                'client_order_ref': label,
                'delivery_quality_profile_id': delivery.id if delivery else False,
                'manufacturing_quality_profile_id': mfg.id if mfg else False,
                'order_line': [(0, 0, {'product_id': widget.id, 'product_uom_qty': 4})],
            })

        so_estandar = make_order('DEMO-ESTANDAR', delivery=prof_estandar, mfg=prof_estandar)
        so_premium = make_order('DEMO-PREMIUM', delivery=prof_premium, mfg=prof_premium)
        # Mixto: distinta calidad por tipo de operación en un mismo pedido
        # (entrega Estándar, manufactura Premium) — muestra que los dos campos
        # del pedido son independientes.
        so_mixto = make_order('DEMO-MIXTO', delivery=prof_estandar, mfg=prof_premium)
        so_nativo = make_order('DEMO-NATIVO')
        so_ninguno = make_order('DEMO-SIN-CONTROLES', delivery=prof_ninguno)
        so_aditivo = make_order('DEMO-ADITIVO', delivery=prof_aditivo)
        all_orders = (so_estandar | so_premium | so_mixto | so_nativo
                      | so_ninguno | so_aditivo)
        all_orders.action_confirm()

        # --- Órdenes de manufactura ligadas por la relación nativa ----------
        def make_mo(order):
            if not order.stock_reference_ids:
                return self.env['mrp.production']
            mo = self.env['mrp.production'].create({
                'product_id': widget.id, 'product_qty': 2.0, 'bom_id': bom.id,
                'reference_ids': [(6, 0, order.stock_reference_ids.ids)]})
            mo.action_confirm()
            return mo

        mo_estandar = make_mo(so_estandar)
        mo_premium = make_mo(so_premium)
        mo_mixto = make_mo(so_mixto)

        # --- Existencias para agilizar la demo ------------------------------
        # NO forzamos la reserva de las ENTREGAS: solo dejamos stock y que Odoo
        # nativo (o un clic manual en "Comprobar disponibilidad") asigne la
        # reserva. Las ventas CON manufactura no deben abastecerse de este
        # stock: primero hay que fabricar su MO (su entrega queda "Not
        # Available" hasta entonces); no forzamos nada para no romper ese flujo.
        #   1) Componente (Sello): stock + reserva de las MO, para que tengan
        #      materias primas listas y puedan producirse sin fricción durante
        #      la prueba (producir sigue exigiendo pasar el QC de manufactura).
        #   2) Producto terminado (Actuador): SOLO stock, para que las ventas
        #      SIN manufactura puedan reservar su entrega (nativa o manualmente)
        #      y probar los controles de calidad por producto (Odoo solo los
        #      ofrece sobre líneas reservadas).
        Quant = self.env['stock.quant']
        stock_location = warehouse.lot_stock_id
        Quant._update_available_quantity(component, stock_location, 100.0)
        (mo_estandar | mo_premium | mo_mixto).action_assign()
        Quant._update_available_quantity(widget, stock_location, 50.0)

        # ==================================================================
        # NARRATIVA DIDÁCTICA
        # ==================================================================
        intro = Markup(
            "<p>📚 <b>Data de aprendizaje — Perfiles de Calidad por Pedido</b></p>"
            "<p>Este módulo permite decidir, <b>desde el pedido de venta</b>, qué "
            "puntos de control de calidad se aplican a sus operaciones de "
            "<b>entrega</b> y de <b>manufactura</b> (la calidad varía según el "
            "cliente y el precio). Odoo crea los controles automáticamente; este "
            "módulo <b>poda o añade</b> sobre ese resultado, sin romper lo nativo.</p>")

        # Nota de "cómo probar" que se anexa a los escenarios de entrega, para
        # anticipar las dudas típicas (reserva/disponibilidad, encadenado del
        # asistente, botón de regenerar y autocompletado de perfiles).
        test_flow_note = Markup(
            "<hr/><p>🧪 <b>Cómo probar los controles (importante):</b></p><ul>"
            "<li><b>Manufactura:</b> en la MO, botón <i>Quality Checks</i> "
            "encadena <b>todos</b> los controles en una sola ventana (al pasar "
            "uno avanza al siguiente). Pásalos y <b>produce</b> la MO.</li>"
            "<li><b>Entrega:</b> los controles <b>por producto</b> solo aparecen "
            "en el asistente cuando el albarán está <b>reservado</b>. Si está "
            "<i>Not Available</i>, fabrica antes o pulsa <i>Comprobar "
            "disponibilidad</i>. ⚠️ Sin reserva, <i>Quality Checks</i> no abre "
            "esos controles y <b>no avisa</b>: es comportamiento nativo de Odoo, "
            "no un fallo del módulo (los pendientes bloquearán la validación).</li>"
            "<li><b>Cambiaste el perfil tras confirmar?</b> Usa el botón "
            "<i>Regenerate Quality Checks</i> del pedido para re-aplicarlo a los "
            "controles pendientes.</li>"
            "<li><b>Campos del pedido:</b> al fijar un perfil, si el otro está "
            "vacío se autocompleta con el mismo (editable; si lo borras, queda "
            "vacío). Puedes divergirlos (fabricar Premium, entregar Estándar).</li>"
            "</ul>")

        # ---- Puntos de control -------------------------------------------
        op_label = {'product': 'por Producto', 'operation': 'por Operación',
                    'move_line': 'por Cantidad'}
        point_profiles = {
            qp_del_dim: prof_estandar | prof_premium,
            qp_del_visual: prof_estandar | prof_premium,
            qp_del_seal: prof_premium,
            qp_mo_torque: prof_estandar | prof_premium,
            qp_mo_first: prof_premium,
            qp_xray: prof_aditivo,
        }
        for point, profiles in point_profiles.items():
            post(point, intro + Markup(
                "<p>🔎 <b>Punto de control:</b> se dispara en operaciones de tipo "
                "<b>%(pt)s</b>, con control <b>%(mo)s</b>.</p>"
                "<p>Incluido en los perfiles: %(profs)s.</p>"
                "<p>Un punto es <i>candidato</i> cuando coincide el tipo de "
                "operación y el producto; el perfil del pedido decide si finalmente "
                "genera (o no) el control.</p>"
            ) % {
                'pt': ", ".join(point.picking_type_ids.mapped('name')),
                'mo': op_label.get(point.measure_on, point.measure_on),
                'profs': links(profiles),
            })

        # ---- Perfiles -----------------------------------------------------
        enforcement_help = {
            'restrict': Markup(
                "<b>Restrictivo (whitelist)</b>: en las operaciones del pedido "
                "SOLO se conservan los controles de los puntos del perfil; el "
                "resto de controles nativos se podan. Una lista vacía ⇒ sin "
                "controles."),
            'additive': Markup(
                "<b>Aditivo</b>: se conservan los controles nativos y además se "
                "<i>fuerzan</i> los puntos del perfil aunque no casaran por "
                "producto (respetando el tipo de operación)."),
        }
        profile_orders = {
            prof_estandar: so_estandar,
            prof_premium: so_premium,
            prof_ninguno: so_ninguno,
            prof_aditivo: so_aditivo,
        }
        for profile, order in profile_orders.items():
            post(profile, intro + Markup(
                "<p>🏷️ <b>Perfil «%(name)s».</b> Comportamiento: %(help)s</p>"
                "<p><b>Puntos incluidos:</b> %(points)s</p>"
                "<p><b>Véalo en acción</b> en el pedido %(order)s. Recuerde: un "
                "perfil de <i>entrega</i> solo afecta puntos de entrega y uno de "
                "<i>manufactura</i> solo a los de manufactura — la separación la da "
                "el tipo de operación de cada punto.</p>"
            ) % {
                'name': profile.name,
                'help': enforcement_help[profile.enforcement],
                'points': links(profile.point_ids) if profile.point_ids
                          else Markup("<i>(ninguno — a propósito)</i>"),
                'order': order._get_html_link(),
            })

        # ---- Pedidos + explicación del resultado --------------------------
        def check_titles(checks):
            rel = checks.filtered(lambda c: c.measure_on in ('operation', 'product'))
            return links(rel.point_id) if rel.point_id else Markup("<i>(ninguno)</i>")

        post(so_estandar, intro + Markup(
            "<p>🧾 <b>Escenario ESTÁNDAR (restrictivo).</b> Perfil de entrega y de "
            "manufactura: %(prof)s.</p>"
            "<p><b>Entrega</b> — controles generados: %(del)s. Solo los del perfil; "
            "por eso NO aparece «Certificado Premium» (%(seal)s), que sí saldría con "
            "el perfil Premium (ver %(prem)s).</p>"
            "<p><b>Manufactura</b> (%(mo)s) — controles generados: %(moc)s.</p>"
        ) % {
            'prof': prof_estandar._get_html_link(),
            'del': check_titles(so_estandar.picking_ids.check_ids),
            'seal': qp_del_seal._get_html_link(),
            'prem': so_premium._get_html_link(),
            'mo': mo_estandar._get_html_link() if mo_estandar else Markup("—"),
            'moc': check_titles(mo_estandar.check_ids) if mo_estandar else Markup("—"),
        } + test_flow_note)

        post(so_premium, intro + Markup(
            "<p>🧾 <b>Escenario PREMIUM (restrictivo).</b> Perfil %(prof)s con MÁS "
            "puntos que Estándar.</p>"
            "<p><b>Entrega</b> — controles: %(del)s (incluye el Certificado Premium).</p>"
            "<p><b>Manufactura</b> (%(mo)s) — controles: %(moc)s (añade la validación "
            "de primera pieza).</p>"
            "<p>Compare con %(est)s para ver cómo, a mismo producto, distinto perfil "
            "⇒ distinta calidad.</p>"
        ) % {
            'prof': prof_premium._get_html_link(),
            'del': check_titles(so_premium.picking_ids.check_ids),
            'mo': mo_premium._get_html_link() if mo_premium else Markup("—"),
            'moc': check_titles(mo_premium.check_ids) if mo_premium else Markup("—"),
            'est': so_estandar._get_html_link(),
        } + test_flow_note)

        post(so_mixto, intro + Markup(
            "<p>🧾 <b>Escenario MIXTO.</b> Demuestra que los dos campos del pedido son "
            "<b>independientes</b>: puedes optar por distinta calidad en cada tipo de "
            "operación.</p>"
            "<p>Perfil de <b>entrega</b>: %(pdel)s · Perfil de <b>manufactura</b>: "
            "%(pmo)s.</p>"
            "<p><b>Entrega</b> — controles (nivel Estándar): %(del)s. NO incluye el "
            "Certificado Premium.</p>"
            "<p><b>Manufactura</b> (%(mo)s) — controles (nivel Premium): %(moc)s. SÍ "
            "incluye la validación de primera pieza.</p>"
            "<p>Así, un mismo pedido fabrica con exigencia Premium pero entrega con "
            "controles Estándar. Compare con %(prem)s (todo Premium) y %(est)s (todo "
            "Estándar).</p>"
        ) % {
            'pdel': prof_estandar._get_html_link(),
            'pmo': prof_premium._get_html_link(),
            'del': check_titles(so_mixto.picking_ids.check_ids),
            'mo': mo_mixto._get_html_link() if mo_mixto else Markup("—"),
            'moc': check_titles(mo_mixto.check_ids) if mo_mixto else Markup("—"),
            'prem': so_premium._get_html_link(),
            'est': so_estandar._get_html_link(),
        } + test_flow_note)

        post(so_nativo, intro + Markup(
            "<p>🧾 <b>Escenario NATIVO (sin perfil).</b> El pedido no define perfiles, "
            "así que el módulo <b>no interviene</b>: Odoo crea todos los controles que "
            "apliquen por tipo de operación/producto.</p>"
            "<p><b>Entrega</b> — controles nativos: %(del)s.</p>"
            "<p>Esto demuestra que sin configuración el comportamiento es 100%% el de "
            "Odoo (no se rompe nada).</p>"
        ) % {'del': check_titles(so_nativo.picking_ids.check_ids)} + test_flow_note)

        post(so_ninguno, intro + Markup(
            "<p>🧾 <b>Escenario SIN CONTROLES.</b> Perfil de entrega %(prof)s: "
            "restrictivo con lista de puntos <b>vacía</b>.</p>"
            "<p><b>Entrega</b> — controles generados: %(del)s. Resultado: ninguno. "
            "Útil para clientes/pedidos sin exigencias de calidad.</p>"
        ) % {
            'prof': prof_ninguno._get_html_link(),
            'del': check_titles(so_ninguno.picking_ids.check_ids),
        })

        post(so_aditivo, intro + Markup(
            "<p>🧾 <b>Escenario ADITIVO.</b> Perfil de entrega %(prof)s (aditivo) con "
            "el punto %(xray)s, que está restringido a otro producto y por eso NO "
            "casaría nativamente en esta entrega.</p>"
            "<p><b>Entrega</b> — controles generados: %(del)s. Se conservan los "
            "nativos y ADEMÁS se fuerza la radiografía.</p>"
            "<p>Contraste con el modo restrictivo de %(est)s, que en vez de añadir, "
            "recorta.</p>"
        ) % {
            'prof': prof_aditivo._get_html_link(),
            'xray': qp_xray._get_html_link(),
            'del': check_titles(so_aditivo.picking_ids.check_ids),
            'est': so_estandar._get_html_link(),
        } + test_flow_note)

        # ---- Controles generados: el "porqué" de cada uno -----------------
        def explain_checks(operation, profile, order, kind):
            for check in operation.check_ids.filtered(
                    lambda c: c.measure_on in ('operation', 'product')):
                in_profile = check.point_id in profile.point_ids
                if profile.enforcement == 'restrict':
                    reason = Markup(
                        "está incluido en el perfil restrictivo %(p)s, por lo que "
                        "sobrevivió a la poda") % {'p': profile._get_html_link()}
                elif in_profile:
                    reason = Markup(
                        "fue <b>forzado</b> por el perfil aditivo %(p)s") % {
                        'p': profile._get_html_link()}
                else:
                    reason = Markup(
                        "lo creó Odoo de forma nativa (el perfil aditivo %(p)s no "
                        "lo quita)") % {'p': profile._get_html_link()}
                post(check, Markup(
                    "<p>✅ <b>Control de calidad</b> en la operación de %(kind)s del "
                    "pedido %(order)s.</p>"
                    "<p>Se generó porque el punto %(point)s %(reason)s.</p>"
                ) % {
                    'kind': kind, 'order': order._get_html_link(),
                    'point': check.point_id._get_html_link(), 'reason': reason,
                })

        explain_checks(so_estandar.picking_ids, prof_estandar, so_estandar, "entrega")
        explain_checks(so_premium.picking_ids, prof_premium, so_premium, "entrega")
        explain_checks(so_mixto.picking_ids, prof_estandar, so_mixto, "entrega")
        explain_checks(so_aditivo.picking_ids, prof_aditivo, so_aditivo, "entrega")
        if mo_estandar:
            explain_checks(mo_estandar, prof_estandar, so_estandar, "manufactura")
        if mo_premium:
            explain_checks(mo_premium, prof_premium, so_premium, "manufactura")
        if mo_mixto:
            explain_checks(mo_mixto, prof_premium, so_mixto, "manufactura")
