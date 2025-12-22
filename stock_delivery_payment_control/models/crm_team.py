from odoo import models, fields

class CRMTeam(models.Model):
    _inherit = 'crm.team'

    payment_control_active = fields.Boolean(
        string="Default Payment Control Active",
        help="If configured, sales orders for this team will have Payment Control enabled by default (unless overridden by Customer settings)."
    )
    payment_validation_level = fields.Selection(
        [('sale', 'Sale Order Level'), ('picking', 'Picking Level')],
        string="Default Validation Level",
        default='sale',
        help="Default validation level for this team's orders."
    )
    include_credit_analysis = fields.Boolean(
        string="Default Include Credit Analysis", 
        default=True,
        help="Default setting for credit analysis inclusion for this team."
    )
    require_full_payment = fields.Boolean(
        string="Default Require Full Payment", 
        default=False,
        help="Default setting for requiring full payment before delivery for this team."
    )
