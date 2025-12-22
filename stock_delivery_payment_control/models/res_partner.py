from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    payment_control_active = fields.Boolean(
        string="Default Payment Control Active",
        help="If configured, sales orders for this customer will have Payment Control enabled by default."
    )
    payment_validation_level = fields.Selection(
        [('sale', 'Sale Order Level'), ('picking', 'Picking Level')],
        string="Default Validation Level",
        default='sale',
        help="Default validation level for this customer's orders."
    )
    include_credit_analysis = fields.Boolean(
        string="Default Include Credit Analysis", 
        default=True,
        help="Default setting for credit analysis inclusion for this customer."
    )
    require_full_payment = fields.Boolean(
        string="Default Require Full Payment", 
        default=False,
        help="Default setting for requiring full payment before delivery for this customer."
    )
