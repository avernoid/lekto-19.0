from odoo import api, fields, models


class EpsEmployeeRelative(models.Model):
    _inherit = "hr.employee.relative"

    percentage_eps = fields.Integer(
        string='EPS (%)',
        help="Percentage of EPS coverage for the relative."
    )
    tax_eps = fields.Integer(
        string='EPS Tax',
        help="Tax amount for EPS."
    )
    payer_eps = fields.Boolean(
        string='EPS Payer',
        help="Indicates if this relative is the payer of the EPS."
    )
    disability = fields.Boolean(
        string='Disability',
        help="Indicates if the relative has a disability."
    )
    max_age = fields.Integer(
        string='Max Age',
        help="Maximum age for EPS coverage."
    )
