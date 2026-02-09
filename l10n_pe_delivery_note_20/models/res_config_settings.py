from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_pe_edi_delivery_test_env = fields.Boolean(
        string="Entorno de prueba GRE",
        related='company_id.l10n_pe_edi_delivery_test_env',
        readonly=False
    )

    @api.onchange('l10n_pe_edi_delivery_test_env')
    def _onchange_l10n_pe_edi_delivery_test_env(self):
        if self.l10n_pe_edi_delivery_test_env:
            self.company_id.l10n_pe_edi_stock_token = False
        else:
            self.company_id.l10n_pe_edi_stock_token = False
