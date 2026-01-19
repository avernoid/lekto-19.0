from odoo import api, fields, models, _

class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.depends('move_id.line_ids.matched_debit_ids', 'move_id.line_ids.matched_credit_ids')
    def _compute_stat_buttons_from_reconciliation(self):
        super(AccountPayment, self)._compute_stat_buttons_from_reconciliation()
        for pay in self:
            serie_correlative = False
            document_type = False
            for move in pay.reconciled_invoice_ids:
                for line in move.line_ids:
                    if line.serie_correlative:
                        serie_correlative = line.serie_correlative
                    if line.l10n_latam_document_type_id:
                        document_type = line.l10n_latam_document_type_id
            for line in pay.move_id.line_ids:
                if line:
                    if document_type:
                        self._cr.execute("""UPDATE account_move_line
                                        SET l10n_latam_document_type_id=%s
                                        WHERE id=%s """,
                                         (document_type.id, line.id))
                    if serie_correlative:
                        self._cr.execute("""UPDATE account_move_line
                                        SET serie_correlative=%s
                                        WHERE id=%s """,
                                        (serie_correlative, line.id))