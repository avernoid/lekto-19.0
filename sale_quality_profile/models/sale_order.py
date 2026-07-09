from odoo import api, fields, models


class SaleOrder(models.Model):
    """Añade al pedido la elección manual de perfiles de calidad para las
    operaciones de manufactura y de entrega que genere la venta."""

    _inherit = 'sale.order'

    manufacturing_quality_profile_id = fields.Many2one(
        'quality.profile', string='Manufacturing Quality Profile',
        help="Quality profile applied to the Manufacturing Orders spawned by "
             "this sale order. Leave empty to keep Odoo's native behavior.")
    delivery_quality_profile_id = fields.Many2one(
        'quality.profile', string='Delivery Quality Profile',
        help="Quality profile applied to the delivery operations of this sale "
             "order. Leave empty to keep Odoo's native behavior.")

    # ------------------------------------------------------------------
    # Comodidad de UI: autocompletado cruzado de perfiles
    # ------------------------------------------------------------------
    # Al elegir uno de los dos perfiles, si el otro está vacío se copia el
    # mismo (la mayoría de pedidos usan el mismo nivel para ambas operaciones).
    # Reglas: nunca pisa un valor ya puesto (editable) y, si luego se limpia el
    # que se autocompletó, queda vacío (el onchange solo copia sobre vacío). Es
    # solo en el formulario: por API/import NO se replica, para no imponer
    # espejo donde el vacío puede ser intencional. Los dos campos siguen siendo
    # independientes (puedes divergirlos, p. ej. fabricar Premium y entregar
    # Estándar).
    @api.onchange('delivery_quality_profile_id')
    def _onchange_delivery_quality_profile_id(self):
        if self.delivery_quality_profile_id and not self.manufacturing_quality_profile_id:
            self.manufacturing_quality_profile_id = self.delivery_quality_profile_id

    @api.onchange('manufacturing_quality_profile_id')
    def _onchange_manufacturing_quality_profile_id(self):
        if self.manufacturing_quality_profile_id and not self.delivery_quality_profile_id:
            self.delivery_quality_profile_id = self.manufacturing_quality_profile_id

    def action_regenerate_quality_checks(self):
        """Regenera los controles de calidad pendientes de las operaciones
        abiertas de la venta, aplicando los perfiles actuales. Útil si se
        cambia el perfil después de confirmar. Solo toca checks en estado
        'none' (no hechos), reutilizando la creación nativa (que vuelve a
        pasar por el filtro de perfil)."""
        for order in self:
            pickings = order.picking_ids.filtered(
                lambda p: p.state not in ('done', 'cancel'))
            pickings.sudo().check_ids.filtered(
                lambda c: c.quality_state == 'none').unlink()
            pickings.move_ids._create_quality_checks()

            mos = order.mrp_production_ids.filtered(
                lambda m: m.state not in ('done', 'cancel'))
            mos.sudo().check_ids.filtered(
                lambda c: c.quality_state == 'none').unlink()
            (mos.move_raw_ids | mos.move_finished_ids)._create_quality_checks_for_mo()
        return True
