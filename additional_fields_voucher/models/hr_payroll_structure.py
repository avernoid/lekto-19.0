from odoo import api, fields, models

class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    law = fields.Text(
        string='Law/Decrees',
        help='Specify the legal basis, laws, or decrees that regulate this payroll structure. This information may appear on related reports or vouchers.'
    )