from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pe_edi_provider = fields.Selection(selection_add=[('ose', 'OSE')])
    l10n_pe_edi_provider_ose_prod_wsdl = fields.Char(string='OSE WSDL')
    l10n_pe_edi_provider_ose_test_wsdl = fields.Char(string='OSE WSDL (Test)')
