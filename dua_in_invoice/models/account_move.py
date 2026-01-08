from datetime import datetime

from odoo import fields, models, api
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    years = [('{}'.format(i), '{}'.format(i)) for i in range(1981, datetime.today().year + 1)]

    year_aduana = fields.Selection(
        string='Year of Emission',
        selection=years,
        help='Year of issuance of the Customs Declaration of Goods - Definitive Import or Simplified Dispatch - Simplified Import.'
    )
    code_aduana = fields.Many2one(
        string='Customs Dependency',
        comodel_name='code.aduana',
        help='Select the Customs Dependency code associated with this document. This code identifies the specific customs office where the declaration was processed.',
    )
    related_document_type_code = fields.Char(
        string='Document Type Code',
        related='l10n_latam_document_type_id.code',
        store=False,
        help='Technical field used to store the code of the selected L10N LATAM Document Type. It is used to conditionally display customs-related fields.'
    )
    
    @api.onchange('l10n_latam_document_type_id')
    def _onchange_l10n_latam_document_type_id(self):
        # [V19 Migration] Replaced old super(Class, self) with new super()
        super()._onchange_l10n_latam_document_type_id()
        if self.move_type not in ['out_invoice', 'out_refund'] and self.l10n_latam_document_type_id.code not in ['50', '52','53']:
            self.code_aduana = False
            self.year_aduana = ''

