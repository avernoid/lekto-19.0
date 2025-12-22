from odoo import models, fields

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    enforce_payment_control = fields.Boolean(
        string="Enforce Payment Control",
        default=False,
        help="If checked, pickings of this type will be subject to payment control validation and will count towards the delivered value of the sale order."
    )

    payment_control_active = fields.Boolean(
        string="Active Payment Control Fallback",
        help="Fallback setting if no policy is defined on the Sale Order."
    )
    payment_validation_level = fields.Selection(
        [('sale', 'Sale Order Level'), ('picking', 'Picking Level')],
        string="Validation Level Fallback",
        default='picking',
        help="Fallback validation level setting."
    )
    include_credit_analysis = fields.Boolean(
        string="Include Credit Analysis Fallback",
        help="Fallback credit analysis setting."
    )
    require_full_payment = fields.Boolean(
        string="Require Full Payment Fallback",
        help="Fallback full payment requirement setting."
    )
