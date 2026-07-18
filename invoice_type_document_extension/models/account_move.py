from odoo import models

# Invoice/refund types that can back a stock movement's PLE document.
_INVOICE_TYPES = ('out_invoice', 'in_invoice', 'out_refund', 'in_refund')


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ------------------------------------------------------------------
    # Event: an invoice/refund got posted (design doc 3.3).
    # _post (NOT action_post) - super-first, because the fiscal number is only
    # assigned by super().  Covers every posting path (auto-post cron, EDI,
    # reconciliation), not just the button.
    # ------------------------------------------------------------------
    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        posted._itde_propagate_to_stock_moves()
        return posted

    def _itde_propagate_to_stock_moves(self):
        """Fill (if empty) the transfer fields on the stock moves this
        invoice/refund backs.  Propagating through ``order_id.picking_ids``
        reaches BOTH the delivery/receipt pickings and the return pickings
        (the return move then resolves its credit note via
        origin_returned_move_id in _itde_document_values)."""
        moves = self.env['stock.move']
        for invoice in self:
            if invoice.move_type not in _INVOICE_TYPES:
                continue
            lines = invoice.invoice_line_ids
            # Purchase side: purchase_line_id is singular on account.move.line.
            moves |= lines.purchase_line_id.order_id.picking_ids.move_ids
            # Sale side: sale_line_ids is the M2M plural on account.move.line
            # (NOT the singular sale_line_id of stock.move).
            moves |= lines.sale_line_ids.order_id.picking_ids.move_ids
        if moves:
            # force=True so the invoice (our top priority) overwrites a value a
            # move may already carry from its remission guide (deliver-first,
            # invoice-later).  manual_override is still respected.
            moves._itde_populate_documents(force=True)

    # ------------------------------------------------------------------
    # Event: invoice reset to draft / cancelled -> the number is no longer
    # valid, so clear the NON-manual fields it populated.  Manual edits and the
    # bridge fallback are untouched; a later re-post re-populates via _post.
    # ------------------------------------------------------------------
    def button_draft(self):
        affected = self._itde_backed_stock_moves()
        res = super().button_draft()
        self._itde_reset_backed_moves(affected)
        return res

    def button_cancel(self):
        affected = self._itde_backed_stock_moves()
        res = super().button_cancel()
        self._itde_reset_backed_moves(affected)
        return res

    def _itde_reset_backed_moves(self, moves):
        """The invoice is no longer posted: drop its (non-manual) value, then
        re-derive so a move falls back to its remission guide instead of going
        blank."""
        moves._itde_clear_auto()
        moves._itde_populate_documents()

    def _itde_backed_stock_moves(self):
        moves = self.env['stock.move']
        for invoice in self:
            if invoice.move_type not in _INVOICE_TYPES:
                continue
            lines = invoice.invoice_line_ids
            moves |= lines.purchase_line_id.order_id.picking_ids.move_ids
            moves |= lines.sale_line_ids.order_id.picking_ids.move_ids
        return moves
