from odoo import fields, models


class MrpEco(models.Model):
    """Extensión de mrp.eco para agregar trazabilidad a la orden de venta.
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
