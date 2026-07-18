from odoo import fields, models


class StockPicking(models.Model):
    """The three transfer fields now live on stock.move (per-movement), not on
    the picking - multi-document-per-picking is common.  The picking keeps only
    a quick-set launcher for the frequent "one picking = one document" case.

    The three legacy picking fields are re-declared below as INERT archive
    fields: same technical names, no compute/inverse, no auto-population, not in
    any view.  Their sole purpose is to keep the historical value that older
    versions stored on the picking readable (it survives as an orphan column
    that these plain fields simply re-attach to).  Nothing reads them for the
    PLE - the report consumes stock.move - so they can never desync the report.
    """

    _inherit = 'stock.picking'

    # --- Legacy / archive only (do NOT add to any view, do NOT compute) ---
    transfer_document_type_id = fields.Many2one(
        comodel_name='l10n_latam.document.type',
        string='Doc Type (legacy)',
        help="Legacy field kept only to preserve the historical value stored on "
             "the picking by older versions. The active PLE 13.1 capture now "
             "lives on the stock movement (stock.move); nothing reads this field.",
    )
    serie_transfer_document = fields.Char(
        string='Serie (legacy)',
        help="Legacy field kept only to preserve historical data. See "
             "Doc Type (legacy).",
    )
    number_transfer_document = fields.Char(
        string='Correlativo (legacy)',
        help="Legacy field kept only to preserve historical data. See "
             "Doc Type (legacy).",
    )

    def action_itde_quickset_transfer_document(self):
        """Open the quick-set wizard to stamp one document onto every move of
        this picking (respects manual_override)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            # No 'name': the dialog title comes from the wizard form's
            # translatable ``string`` (avoids an untranslated hardcoded label).
            'res_model': 'stock.transfer.document.quickset',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_picking_id': self.id},
        }
