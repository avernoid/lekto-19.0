from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    serie_correlative = fields.Char(
        string='Series-Correlative',
        help='Official document number (Series-Number) propagated from the invoice.',
        compute='_compute_serie_correlative_payment',
        store=True,
    )

    @api.depends('ref', 'name', 'l10n_latam_document_number')
    def _compute_serie_correlative_payment(self):
        for move in self:
            if move.move_type in ['in_invoice', 'in_refund', 'in_receipt']:
                document_number = move.l10n_latam_document_number or move.ref
                move.serie_correlative = document_number.replace(' ', '') if document_number else False
                (move.invoice_line_ids | move.line_ids).write({'serie_correlative': move.serie_correlative})
            elif move.move_type in ['out_invoice', 'out_refund', 'out_receipt'] and not move.journal_id.l10n_latam_use_documents and move.journal_id.type != 'sale':
                continue
            elif move.move_type in ['out_invoice', 'out_refund', 'out_receipt']:
                move.serie_correlative = move.name
                (move.invoice_line_ids | move.line_ids).write({'serie_correlative': move.name})
            elif move.move_type == 'entry':
                ids = [line.id for line in move.line_ids._all_reconciled_lines()]
                if ids:
                    self.env.cr.execute("""
                        SELECT l10n_latam_document_type_id, serie_correlative
                        FROM account_move_line
                        WHERE id in %s and serie_correlative is not NULL""", [tuple(ids)]
                    )
                    is_document_type = self.env.cr.dictfetchall()
                    if is_document_type:
                        document_type = is_document_type[0]['l10n_latam_document_type_id']
                        serie_correlative = is_document_type[0]['serie_correlative']
                        for id_line in ids:
                            self.env.cr.execute("""
                                SELECT l10n_latam_document_type_id, serie_correlative
                                FROM account_move_line
                                WHERE id=%s """, [(id_line)]
                            )
                            is_document_type = self.env.cr.dictfetchall()
                            if not is_document_type[0]['l10n_latam_document_type_id']:
                                self.env['account.move.line'].search([('id', '=', id_line)]).write({
                                    'l10n_latam_document_type_id': document_type,
                                    'serie_correlative': serie_correlative
                                })

    def _compute_name(self):
        super()._compute_name()
        for move in self:
            if move.move_type in ['out_invoice', 'out_refund', 'out_receipt']:
                for line in move.invoice_line_ids:
                    line.serie_correlative = move.name
                for line in move.line_ids:
                    line.serie_correlative = move.name





