import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MrpEco(models.Model):
    """Extensión de mrp.eco para:
    1. Trazabilidad a la orden de venta que originó el ECO (sale_id).
    2. Generación de la Orden de Manufactura (MO) al aprobar el ECO, ligada a
       esa venta como su abastecimiento real (cadena MTO nativa).

    El modelo nativo de mrp.eco en Odoo 19 NO tiene relación con sale.order,
    por lo que la agregamos aquí para vincular cada ECO con la SO que lo generó."""

    _inherit = 'mrp.eco'

    sale_id = fields.Many2one(
        comodel_name='sale.order',
        string="Source sale order",
        index=True,
        readonly=True,
        help="Sale order whose confirmation triggered the automatic creation "
             "of this ECO. Empty for ECOs created manually.",
    )
    sale_order_name = fields.Char(
        string="Source sale order reference",
        related='sale_id.name',
        readonly=True,
        help="Reference number of the sale order that originated this ECO, "
             "shown for traceability.",
    )
    # MO generada POR este ECO para abastecer la venta. Es un campo propio y NO
    # el nativo `production_id` (que significa "MO que ORIGINÓ el ECO" y se usa
    # en mrp_plm action_new_revision; reutilizarlo rompería la revisión de BoM).
    generated_production_id = fields.Many2one(
        comodel_name='mrp.production',
        string="Generated Manufacturing Order",
        readonly=True,
        copy=False,
        index='btree_not_null',
        help="Manufacturing Order created from this ECO to supply its source "
             "sale order. Used to keep MO creation idempotent.",
    )
    # Espejo de la marca nativa 'Final Stage' de la etapa actual, para poder
    # condicionar en la vista que el botón manual de crear MO solo aparezca en
    # las etapas finales (donde el ECO queda tras aplicar los cambios).
    stage_is_final = fields.Boolean(
        string="ECO is in a final stage",
        related='stage_id.final_stage',
    )

    # ------------------------------------------------------------------
    # Triggers
    # ------------------------------------------------------------------
    def write(self, vals):
        """Extiende write para detectar la transición de etapa que dispara la
        creación automática de la MO. Solo actúa cuando el ECO entra en una
        etapa marcada con triggers_mo_creation y su tipo tiene auto_create_mo.
        Es no bloqueante: cualquier fallo se registra sin romper el write."""
        res = super().write(vals)
        if vals.get('stage_id'):
            stage = self.env['mrp.eco.stage'].browse(vals['stage_id'])
            if stage.triggers_mo_creation:
                for eco in self:
                    if not eco.type_id.auto_create_mo:
                        continue
                    try:
                        eco._create_manufacturing_order_for_sale()
                    except Exception:
                        # No bloquear el cambio de etapa por un fallo al crear
                        # la MO; queda registrado para diagnóstico.
                        _logger.exception(
                            "Error al crear automáticamente la Orden de "
                            "Manufactura para el ECO '%s' (venta '%s').",
                            eco.name, eco.sale_id.name,
                        )
        return res

    def action_create_sale_manufacturing_order(self):
        """Botón manual: crea la MO para la venta de origen.
        Disponible siempre (ignora el gate auto_create_mo del tipo), pero
        respeta idempotencia y precondiciones. Al ser acción explícita del
        usuario, los problemas se reportan con UserError."""
        self.ensure_one()
        self._create_manufacturing_order_for_sale(raise_if_invalid=True)
        if self.generated_production_id:
            return self.action_open_generated_production()
        return False

    def action_open_generated_production(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Manufacturing Order"),
            'res_model': 'mrp.production',
            'res_id': self.generated_production_id.id,
            'view_mode': 'form',
        }

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------
    def _create_manufacturing_order_for_sale(self, raise_if_invalid=False):
        """Crea la Orden de Manufactura que abastece la venta de origen,
        encadenándola al movimiento de entrega vía la cadena MTO nativa.

        Reutiliza el motor de procura de Odoo: ejecuta la regla de fabricación
        con `move_dest_ids` = movimiento(s) de entrega de la venta, de modo que
        `_run_manufacture` crea la MO ya enlazada (el movimiento de producto
        terminado hereda `move_dest_ids` en `_get_move_finished_values`).

        Idempotente: si ya hay una MO generada/vinculada vigente, no crea otra.

        :param raise_if_invalid: si True, lanza UserError ante precondiciones
            no cumplidas (uso desde el botón manual). Si False, simplemente
            retorna sin crear (uso desde el disparo automático)."""
        self.ensure_one()
        # Se eleva a sudo: quien confirma la venta o mueve la etapa puede no
        # tener permisos sobre stock/mrp.
        eco = self.sudo()

        def _bail(msg):
            if raise_if_invalid:
                raise UserError(msg)
            return False

        # 1. Idempotencia: MO ya generada y no cancelada.
        if eco.generated_production_id and eco.generated_production_id.state != 'cancel':
            return _bail(_(
                "A Manufacturing Order (%s) was already created from this ECO.",
                eco.generated_production_id.name,
            ))

        # 2. Origen: requiere venta y producto.
        if not eco.sale_id:
            return _bail(_("This ECO is not linked to a sale order."))
        if not eco.product_tmpl_id:
            return _bail(_("This ECO has no product set."))

        # 3. Líneas de venta del producto (almacenable).
        order = eco.sale_id
        product_tmpl = eco.product_tmpl_id
        lines = order.order_line.filtered(
            lambda l: l.product_id.product_tmpl_id == product_tmpl
            and l.product_id.type == 'consu'
            and l.product_id.is_storable
        )
        if not lines:
            return _bail(_(
                "No storable sale order line for product '%s' found on %s.",
                product_tmpl.display_name, order.name,
            ))

        # 4. Movimientos de entrega abiertos (salientes) de esas líneas.
        delivery_moves = lines.move_ids.filtered(
            lambda m: m.state not in ('done', 'cancel')
            and (m.location_final_id or m.location_dest_id)._is_outgoing()
        )
        if not delivery_moves:
            return _bail(_(
                "No open delivery move to supply for product '%s' on %s.",
                product_tmpl.display_name, order.name,
            ))

        # 4b. Idempotencia adicional: si alguna entrega ya está abastecida por
        # una MO vigente, reutilizarla y no crear otra.
        existing_mo = delivery_moves.created_production_id.filtered(
            lambda p: p.state != 'cancel'
        )
        if existing_mo:
            eco.generated_production_id = existing_mo[:1]
            return _bail(_(
                "A Manufacturing Order (%s) already supplies this sale.",
                existing_mo[:1].name,
            ))

        # 5. BoM usable (con componentes) para el/los producto(s).
        products = lines.product_id
        bom_by_product = self.env['mrp.bom']._bom_find(
            products, company_id=order.company_id.id, bom_type='normal')
        if not any(bom_by_product.get(p) and bom_by_product[p].bom_line_ids
                   for p in products):
            return _bail(_(
                "Product '%s' has no usable Bill of Materials yet; complete "
                "the BoM before creating the Manufacturing Order.",
                product_tmpl.display_name,
            ))

        # 6. Lanzar la procura de fabricación encadenada a las entregas.
        Procurement = self.env['stock.rule'].Procurement
        procurements = []
        for move in delivery_moves:
            warehouse = move.warehouse_id or move.picking_type_id.warehouse_id \
                or move.location_id.warehouse_id
            manufacture_route = warehouse.manufacture_pull_id.route_id
            if not manufacture_route:
                return _bail(_(
                    "Warehouse '%s' has no manufacture route configured.",
                    warehouse.display_name,
                ))
            # Liberar la reserva y convertir en MTO para que la entrega quede a
            # la espera de la MO y reserve exactamente lo producido.
            move._do_unreserve()
            move.procure_method = 'make_to_order'
            values = move._prepare_procurement_values()
            # Forzar la ruta de fabricación (el producto puede no tenerla,
            # justamente porque al confirmar la venta aún no había BoM).
            values['route_ids'] = manufacture_route
            procurements.append(Procurement(
                move.product_id, move.product_uom_qty, move.product_uom,
                move.location_id,
                move.rule_id.name or order.name, order.name,
                move.company_id, values,
            ))

        self.env['stock.rule'].run(procurements)

        # 7. Capturar la MO creada y fijar el vínculo idempotente.
        mo = delivery_moves.created_production_id.filtered(
            lambda p: p.state != 'cancel')[:1]
        if not mo:
            return _bail(_(
                "The Manufacturing Order could not be created for '%s'.",
                product_tmpl.display_name,
            ))
        eco.generated_production_id = mo
        eco.message_post(body=_(
            "Manufacturing Order %s created to supply sale order %s.",
            mo.name, order.name,
        ))
        order.message_post(body=_(
            "Manufacturing Order %s created from ECO %s.",
            mo.name, eco.name,
        ))
        return mo
