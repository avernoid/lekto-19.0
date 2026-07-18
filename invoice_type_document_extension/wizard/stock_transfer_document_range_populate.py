from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import config

_ITDE_BATCH_SIZE = 1000


class StockTransferDocumentRangePopulate(models.TransientModel):
    """Re-runnable maintenance tool: populate the PLE transfer document on the
    stock movements of a chosen date range, without depending on the one-shot
    upgrade migration.  Two modes:

    * re-derive from the invoices / remission guides (the normal capture logic);
    * copy the legacy value stored on the picking (for periods older than the
      migration window), via raw SQL so long historical numbers never trip the
      SUNAT format constraint.
    Both run in batches with commits so they scale to very large tables.
    """

    _name = 'stock.transfer.document.range.populate'
    _description = 'Populate PLE transfer document over a date range'

    date_from = fields.Date(
        string='From', required=True,
        help="Include stock movements done on or after this date.",
    )
    date_to = fields.Date(
        string='To', required=True,
        help="Include stock movements done on or before this date.",
    )
    mode = fields.Selection(
        selection=[
            ('rederive', 'Re-derive from invoices / remission guides'),
            ('copy_legacy', 'Copy legacy picking values'),
        ],
        default='rederive', required=True,
        help="Re-derive: recompute the document from each movement's invoice or "
             "remission guide (fill-if-empty, or overwrite non-manual with the "
             "option below).\n"
             "Copy legacy: copy the value older versions stored on the picking "
             "onto its movements (for periods older than the migration window).",
    )
    overwrite = fields.Boolean(
        string='Overwrite non-manual values',
        help="Re-derive mode only: also overwrite movements that already carry a "
             "non-manual value. Manual edits are always preserved.",
    )

    def action_run(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_("The 'From' date must not be after the 'To' date."))
        if self.mode == 'copy_legacy':
            self._itde_copy_legacy_range()
        else:
            self._itde_rederive_range()
        return {'type': 'ir.actions.act_window_close'}

    def _itde_rederive_range(self):
        Move = self.env['stock.move']
        domain = [
            ('state', '=', 'done'),
            ('product_id.is_storable', '=', True),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        offset = 0
        while True:
            batch = Move.search(
                domain, offset=offset, limit=_ITDE_BATCH_SIZE, order='id')
            if not batch:
                break
            batch._itde_populate_documents(force=self.overwrite)
            if not config['test_enable']:
                self.env.cr.commit()  # batch checkpoint (forbidden under tests)
            self.env.invalidate_all()
            offset += _ITDE_BATCH_SIZE

    def _itde_copy_legacy_range(self):
        if 'transfer_document_type_id' not in self.env['stock.picking']._fields:
            raise UserError(_(
                "There are no legacy picking columns to copy from on this "
                "database."))
        # Reuse the shared SQL copy (same as the 'Recover Serie & Correlativo'
        # move action and the upgrade migration), bounded to the date range.
        self.env['stock.move']._itde_copy_legacy_sql(
            "AND sm.date >= %s AND sm.date < (%s::date + 1)",
            [self.date_from, self.date_to],
        )
        self.env.invalidate_all()
