import logging

from odoo import models

_logger = logging.getLogger(__name__)

# Solo filtramos/añadimos checks a estos niveles. Los de tipo 'move_line'
# (por cantidad) se crean en otro momento y se dejan en comportamiento nativo.
_FILTERED_MEASURE_ON = ('operation', 'product')


class StockMove(models.Model):
    _inherit = 'stock.move'

    # ------------------------------------------------------------------
    # Delivery (quality_control)
    # ------------------------------------------------------------------
    def _create_quality_checks(self):
        """Extiende la creación nativa de checks de transferencia: tras crear
        los nativos, aplica el perfil de calidad de ENTREGA del pedido de venta
        de cada picking. Si el picking no tiene venta o la venta no define
        perfil de entrega, no se toca nada (comportamiento nativo)."""
        super()._create_quality_checks()
        for picking in self.picking_id:
            # picking.sale_id es computado por sale_stock a partir de los
            # move_ids.sale_line_id.order_id (resuelve una única venta).
            sale = picking.sale_id
            profile = sale.delivery_quality_profile_id if sale else False
            if not profile:
                continue
            self._apply_quality_profile(
                picking.sudo().check_ids, profile,
                picking.move_ids.product_id, picking.picking_type_id,
                {'picking_id': picking.id}, picking.company_id.id)

    # ------------------------------------------------------------------
    # Manufacturing (quality_mrp)
    # ------------------------------------------------------------------
    def _create_quality_checks_for_mo(self):
        """Extiende la creación nativa de checks de manufactura: tras crear los
        nativos, aplica el perfil de calidad de MANUFACTURA del pedido de venta
        que originó la MO (resuelto vía reference_ids.sale_ids)."""
        super()._create_quality_checks_for_mo()
        for production in self.production_id:
            sales = production.reference_ids.sale_ids
            # Guard conservador: solo si la MO mapea a una única venta.
            if len(sales) != 1:
                if len(sales) > 1 and sales.manufacturing_quality_profile_id:
                    _logger.info(
                        "MO %s mapea a varias ventas; se omite el filtro de "
                        "perfil de calidad para no alterar el comportamiento "
                        "nativo.", production.display_name)
                continue
            profile = sales.manufacturing_quality_profile_id
            if not profile:
                continue
            # Para el forzado 'additive' en una MO, los checks por producto solo
            # admiten el/los producto(s) fabricado(s) (constraint nativo
            # quality_mrp _check_allowed_product_ids_with_production), no los
            # componentes.
            products = production.move_finished_ids.product_id
            self._apply_quality_profile(
                production.sudo().check_ids, profile, products,
                production.picking_type_id,
                {'production_id': production.id}, production.company_id.id)

    # ------------------------------------------------------------------
    # Shared
    # ------------------------------------------------------------------
    def _apply_quality_profile(self, checks, profile, products, picking_type,
                               link_vals, company_id):
        """Aplica un quality.profile sobre los checks recién creados de una
        operación (picking o MO).

        - restrict: conserva solo los checks cuyos puntos están en el perfil
          (whitelist); elimina el resto (solo los pendientes 'none').
        - additive: mantiene los nativos y FUERZA los puntos del perfil que aún
          no tengan check en la operación (aunque no casen por producto),
          respetando el tipo de operación del punto.

        Solo actúa sobre checks measure_on in ('operation','product') y en
        estado 'none'. Poda/añade sobre el resultado ya creado por Odoo; no
        reimplementa el emparejamiento nativo."""
        relevant = checks.filtered(
            lambda c: c.measure_on in _FILTERED_MEASURE_ON
            and c.quality_state == 'none')

        if profile.enforcement == 'restrict':
            to_remove = relevant.filtered(
                lambda c: c.point_id not in profile.point_ids)
            if to_remove:
                to_remove.sudo().unlink()
            return

        # additive: forzar los puntos del perfil que falten en la operación.
        present_points = relevant.point_id
        missing_points = profile.point_ids.filtered(
            lambda p: p not in present_points
            and p.measure_on in _FILTERED_MEASURE_ON
            and p.check_execute_now()
            and (not p.picking_type_ids or picking_type in p.picking_type_ids))
        if not missing_points:
            return
        check_vals_list = []
        for point in missing_points:
            base_vals = {
                'point_id': point.id,
                'team_id': point.team_id.id,
                'measure_on': point.measure_on,
                'company_id': company_id,
                **link_vals,
            }
            if point.measure_on == 'operation':
                check_vals_list.append(base_vals)
            else:  # 'product': un check por producto de la operación
                for product in products:
                    check_vals_list.append({**base_vals, 'product_id': product.id})
        if check_vals_list:
            self.env['quality.check'].sudo().create(check_vals_list)
