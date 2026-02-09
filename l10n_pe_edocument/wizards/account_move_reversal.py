from odoo import models, fields
from odoo.tools.translate import _


refund_reason_13 = ('13', 'Correction of the net amount pending payment and/or due dates')


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    l10n_pe_edi_refund_reason = fields.Selection(selection_add=[refund_reason_13])

    def _prepare_default_reversal(self, move):
        values = super()._prepare_default_reversal(move)
        if self.country_code == 'PE' and move.journal_id.l10n_latam_use_documents:
            values.update({
                'ref': move.ref,
                'l10n_pe_edi_cancel_reason': _(f"Reversal of: {move.name.replace(' ', '')}{f', {self.reason}' if self.reason else ''}")
            })
            if 'l10n_latam_document_type_id' in values.keys() :
                if self.l10n_latam_document_number and '|' in self.l10n_latam_document_number:
                    part_document = self.l10n_latam_document_number
                    values.update({
                        'l10n_latam_document_type_id': int(part_document.split('|')[0]) if part_document.split('|')[0] else
                        values['l10n_latam_document_type_id']
                    })
        return values
