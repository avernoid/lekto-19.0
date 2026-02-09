from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_pe_edi_provider_ose_prod_wsdl = fields.Char(
        string='OSE WSDL',
        related='company_id.l10n_pe_edi_provider_ose_prod_wsdl',
        readonly=False,
    )
    l10n_pe_edi_provider_ose_test_wsdl = fields.Char(
        string='OSE WSDL (Test)',
        related='company_id.l10n_pe_edi_provider_ose_test_wsdl',
        readonly=False,
    )
