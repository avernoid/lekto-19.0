from odoo import models, fields

class CrmTeam(models.Model):
    _inherit = 'crm.team'

    skip_invoice_wizard = fields.Boolean(
        string="Skip Invoice Wizard",
        help="If checked, the invoice wizard will be skipped and a draft invoice will be created automatically when clicking 'Create Invoice' on a Sales Order."
    )
    create_posted_invoice = fields.Boolean(
        string="Create Posted Invoice",
        help="If checked, the created invoice will be automatically posted (validated). This only works if 'Skip Invoice Wizard' is also checked."
    )
