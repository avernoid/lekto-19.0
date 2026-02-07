from odoo import fields, models, api
import logging
_logger = logging.getLogger(__name__)

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def _get_default_exchange_rate(self):
        # Default to today's rate for manual creation
        return self._get_rate_helper(fields.Date.context_today(self), self.currency_id, self.company_id)

    to_force_exchange_rate = fields.Float(
        string='Force Exchange Rate',
        digits=(12, 12),
        default=_get_default_exchange_rate,
        help='Use this field to manually override the exchange rate. If set, this rate will be applied to the Journal Entry instead of the daily system rate.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'to_force_exchange_rate' not in vals and vals.get('currency_id'):
                # API/Code creation: 'default' function lacks access to 'currency_id' in vals.
                # So we calculate it here based on the provided values.
                currency = self.env['res.currency'].browse(vals['currency_id'])
                company = self.env['res.company'].browse(vals.get('company_id') or self.env.company.id)
                date = vals.get('date') or fields.Date.context_today(self)
                
                vals['to_force_exchange_rate'] = self._get_rate_helper(date, currency, company)
                
        return super().create(vals_list)

    @api.model
    def _get_rate_helper(self, date, currency, company):
        if not currency or not company:
            currency = currency or self.env.company.currency_id
            company = company or self.env.company
            
        if currency == company.currency_id:
            return 1.0
            
        return self.env['res.currency']._get_conversion_rate(
            from_currency=company.currency_id,
            to_currency=currency,
            company=company,
            date=date or fields.Date.context_today(self),
        )

    @api.onchange('date', 'currency_id', 'company_id')
    def _onchange_update_force_exchange_rate(self):
        if self.date:
             self.to_force_exchange_rate = self._get_rate_helper(self.date, self.currency_id, self.company_id)

    def _prepare_move_vals(self, force_company_currency=False):
        res = super()._prepare_move_vals(force_company_currency=force_company_currency)
        if self.to_force_exchange_rate:
            res['invoice_currency_rate'] = self.to_force_exchange_rate
        
        # Ensure linkage for precedence logic
        # We pass 'origin_payment_id' explicitly so that during account.move.create(),
        # the compute method _compute_invoice_currency_rate can see the link immediately
        # and PRIORITIZE our forced rate instead of falling back to system rate.
        res['origin_payment_id'] = self.id
        return res

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        ''' Override to apply Forced Exchange Rate to the Lines (Debit/Credit) BEFORE they are created.
            This avoids the need for fragile post-save recalculations.
        '''
        line_vals_list = super()._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals, force_balance=force_balance)

        if self.to_force_exchange_rate:
            # Native Odoo Rate Logic (Indirect):
            # 1 Unit Base (PEN) = X Unit Foreign (USD)
            # Therefore: AmountBase (Balance) = AmountForeign / Rate
            rate = self.to_force_exchange_rate
            
            for line in line_vals_list:
                # Skip lines that are already in Company Currency (e.g. Tax base sometimes, or generic lines)
                # But typically Payment lines are Liquidity (Bank) and Counterpart (Receivable/Payable)
                currency_id = line.get('currency_id')
                if not currency_id:
                    continue

                if currency_id == self.company_id.currency_id.id:
                    continue
                
                amount_currency = line.get('amount_currency', 0.0)
                
                # Apply Native Conversion Logic
                if rate > 0.0:
                    balance = amount_currency / rate
                else:
                    balance = 0.0
                
                # Rounding is critical for Accounting
                balance = self.company_id.currency_id.round(balance)

                _logger.info(f"FORCED_RATE_CALC: Amount={amount_currency}, Rate={rate}, NewBalance={balance}")

                line.update({
                    'balance': balance,
                    'debit': balance if balance > 0.0 else 0.0,
                    'credit': -balance if balance < 0.0 else 0.0,
                })
        
        return line_vals_list
