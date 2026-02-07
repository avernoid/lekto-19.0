from odoo import api, fields, models

import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    # invoice_currency_rate is NATIVE (stored=True).
    # We must override the compute to ensure it respects our forced rate priority.

    @api.depends('currency_id', 'company_currency_id', 'company_id', 'invoice_date', 'taxable_supply_date', 'date', 'move_type', 'origin_payment_id.to_force_exchange_rate')
    def _compute_invoice_currency_rate(self):
        super()._compute_invoice_currency_rate()
        
        for move in self:
            # 1. PRIORITY: If linked to a Payment with a Forced Rate, use it.
            # This ensures that even if Date changes or record is created, the Forced Value persists.
            if move.origin_payment_id and move.origin_payment_id.to_force_exchange_rate:
                move.invoice_currency_rate = move.origin_payment_id.to_force_exchange_rate
            
            # 2. FALLBACK: For Manual Entries, default to expected rate ONLY if empty/zero.
            elif move.move_type == 'entry' and not move.is_invoice(include_receipts=True):
                 if not move.invoice_currency_rate:
                    move.invoice_currency_rate = move.expected_currency_rate

        

