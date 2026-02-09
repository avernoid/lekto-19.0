from odoo import models


class AccountDebitNote(models.TransientModel):
    _inherit = 'account.debit.note'

    def _prepare_default_values(self, move):
        values = super()._prepare_default_values(move)
        if self.country_code == 'PE' and move.journal_id.l10n_latam_use_documents:
            values.update({
                'ref': move.ref,
                'l10n_pe_edi_cancel_reason': f"{move.name.replace(' ', '')}, {self.reason}" if self.reason else move.name
            })
        return values
