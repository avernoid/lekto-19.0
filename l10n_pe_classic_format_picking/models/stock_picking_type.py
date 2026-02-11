from odoo import models, fields


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    show_lot_on_eguia = fields.Boolean(
        string="Serie/Lote en e-Guía",
        default=False,
        help="Display Lot/Serial Number column in the Classic Format Picking report (e-Guía).",
    )
    show_expiry_on_eguia = fields.Boolean(
        string="Expiration Date en e-Guía",
        default=False,
        help="Display Expiration Date column in the Classic Format Picking report (e-Guía). Requires 'Serie/Lote en e-Guía' to be enabled.",
    )
