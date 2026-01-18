from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    additional_information = fields.Html(
        string='Additional Information on Printed Invoice',
        help='Text or HTML that will be printed automatically at the bottom of customer invoices (e.g. Terms and Conditions, Bank Accounts).'
    )
