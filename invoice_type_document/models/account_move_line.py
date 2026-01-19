from odoo import api, fields, models, _

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    serie_correlative = fields.Char(
        string='Series-Correlative',
        help='Official document number (Series-Number) propagated from the invoice.',
        store=True
    )
    move_type = fields.Selection(
        related='move_id.move_type'
    )
    serie_correlative_is_readonly = fields.Boolean(
        string='Is Editable',
        help='Technical field to determine if the Series-Correlative can be edited.',
        compute='_compute_serie_correlative_is_readonly',
        store=True
    )

    def create(self, vals_list):
        lines = super(AccountMoveLine, self).create(vals_list)
        index = 0
        for line in lines:
            if vals_list and isinstance(vals_list, list) and 'l10n_latam_document_type_id' in vals_list[index].keys():
                doc = self.env['l10n_latam.document.type'].search([('id', '=', vals_list[index]['l10n_latam_document_type_id'])])
                if doc.id >= 0:
                    line.l10n_latam_document_type_id = doc
            index += 1
        return lines

    @api.depends('move_id')
    def _compute_serie_correlative_is_readonly(self):
        for rec in self:
            if rec.move_id:
                if rec.move_id.move_type in ['out_invoice', 'out_refund',
                                             'out_receipt'] and not rec.move_id.journal_id.l10n_latam_use_documents and rec.move_id.journal_id.type == 'sale':
                    rec.serie_correlative_is_readonly = False
                elif rec.move_id.move_type == 'entry':
                    rec.serie_correlative_is_readonly = False
                else:
                    rec.serie_correlative_is_readonly = True

    # Extract type of document from the invoices to the other accounting entries
    def reconcile(self):
        res = super(AccountMoveLine, self).reconcile()
        
        account_reconcile = self.env['account.partial.reconcile'].search([('debit_move_id','in',tuple(self.ids))],limit=1)
        document_type = None
        serie_correlative = None
        ids = []

        def update_info(move_line):
            nonlocal document_type, serie_correlative
            if move_line.move_id.l10n_latam_document_type_id and move_line.move_id.serie_correlative:
                document_type = move_line.move_id.l10n_latam_document_type_id
                serie_correlative = move_line.move_id.serie_correlative

        for move_line in account_reconcile.full_reconcile_id.reconciled_line_ids:
            update_info(move_line)
            if move_line.move_id.move_type == 'entry':
                ids.extend([line.id for line in move_line.move_id.line_ids._all_reconciled_lines()])
                    
        if self.full_reconcile_id:
            for line in self.full_reconcile_id.reconciled_line_ids:
                update_info(line)
                
        if document_type and ids:
            ids.append(ids[-1] - 1)
            for id_line in ids:
                self.env.cr.execute("""SELECT l10n_latam_document_type_id 
                                            FROM account_move_line
                                            WHERE id=%s """, [(id_line)])
                is_document_type = self.env.cr.dictfetchall()
                if is_document_type and is_document_type[0] and not is_document_type[0]['l10n_latam_document_type_id']:
                    self.search([('id', '=', id_line)]).write({
                            'l10n_latam_document_type_id': document_type.id,
                            'serie_correlative': serie_correlative
                        })
        if self.statement_id and document_type:
            for line in self.statement_id.line_ids:
                for move_line in line.move_id.line_ids:
                    if document_type and serie_correlative:
                        move_line.l10n_latam_document_type_id = document_type
                        move_line.serie_correlative = serie_correlative
            
        return res