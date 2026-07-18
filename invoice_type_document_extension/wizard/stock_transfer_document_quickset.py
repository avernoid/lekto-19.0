from odoo import fields, models


class StockTransferDocumentQuickset(models.TransientModel):
    """Quick-set: stamp one document (type + serie + number) onto every move of
    a picking - the common "one picking = one document" case.  Writes with
    ``auto_populate=True`` and skips moves flagged ``manual_override``."""

    _name = 'stock.transfer.document.quickset'
    _description = 'Quick-set PLE transfer document on a picking'

    picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Picking',
        required=True,
        help="Transfer whose movements will receive the document.",
    )
    transfer_document_type_id = fields.Many2one(
        comodel_name='l10n_latam.document.type',
        string='Doc Type',
        domain="[('country_id.code', '=', 'PE')]",
        required=True,
        help="Document type (SUNAT table 10) to stamp on every movement of "
             "this transfer for the PLE 13.1 (Kardex).",
    )
    serie_transfer_document = fields.Char(
        string='Serie', required=True,
        help="Document series to stamp on every movement of this transfer.",
    )
    number_transfer_document = fields.Char(
        string='Correlativo', required=True,
        help="Document number (folio) to stamp on every movement of this transfer.",
    )
    override_manual = fields.Boolean(
        string='Overwrite manual edits',
        help="If enabled, also overwrite movements whose document was edited by "
             "hand. If disabled, manual movements are left untouched.",
    )

    def action_apply(self):
        self.ensure_one()
        moves = self.picking_id.move_ids
        if not self.override_manual:
            moves = moves.filtered(lambda m: not m.manual_override)
        moves.with_context(auto_populate=True).write({
            'transfer_document_type_id': self.transfer_document_type_id.id,
            'serie_transfer_document': self.serie_transfer_document,
            'number_transfer_document': self.number_transfer_document,
        })
        return {'type': 'ir.actions.act_window_close'}
