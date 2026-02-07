from odoo import api, models
import logging
_logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends('currency_id', 'company_id', 'move_id.invoice_currency_rate', 'move_id.date')
    def _compute_currency_rate(self):
        super()._compute_currency_rate()
        for line in self:
            # Native Odoo ignores invoice_currency_rate for non-invoices (Entries).
            # We enforce it here if a value is present (from Payment or Manual Entry).
            if not line.move_id.is_invoice(include_receipts=True) and line.move_id.invoice_currency_rate:
                line.currency_rate = line.move_id.invoice_currency_rate
            
            # Note: We NO LONGER re-calculate balance here (check_move_validity=False).
            # The balance is Pre-Calculated in account.payment.
            # This method now only serves to display the correct rate in the UI/Form.
