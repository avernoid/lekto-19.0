from odoo import api, fields, models


class AccountDebitNote(models.TransientModel):
    _inherit = 'account.debit.note'

    def _prepare_default_values(self, move):
        default_values = super(AccountDebitNote, self)._prepare_default_values(move)
        if default_values['debit_origin_id']:
            debit_origin_id = self.env['account.move'].browse(default_values['debit_origin_id'])
            document_type, invoice_date, number = self.get_data_from_origin_debit_note_move_id(debit_origin_id)
            default_values.update({
                'origin_l10n_latam_document_type_id': document_type,
                'origin_number': number,
                'origin_invoice_date': invoice_date
            })
        return default_values

    @staticmethod
    def get_data_from_origin_debit_note_move_id(origin_move_id):
        document_type = False
        invoice_date = False
        number = False
        if origin_move_id and origin_move_id.l10n_latam_document_type_id:
            if origin_move_id.payment_reference:
                number = origin_move_id.payment_reference.replace(' ', '')
            elif origin_move_id.ref:
                number = origin_move_id.ref.replace(' ', '')
            else:
                number = ''
            document_type = origin_move_id.l10n_latam_document_type_id.id
            invoice_date = origin_move_id.invoice_date
        return document_type, invoice_date, number