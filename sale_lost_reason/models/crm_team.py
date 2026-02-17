from odoo import fields, models

class CrmTeam(models.Model):
    _inherit = 'crm.team'

    use_lost_reason = fields.Boolean('Use Lost Reason', default=False, help="If checked, the 'Lost Reason' will be asked when cancelling a sales order.")
