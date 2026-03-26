from ..services.mobilvendor_api import MobilvendorAPIHandler
from odoo import models, fields, api
import requests
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    mobilvendor_id = fields.Char(string='Mobilvendor ID', index=True)

    mobilvendor_invoice_ids = fields.Many2many(
        'account.move',
        'payment_invoice_mobilvendor_rel',
        'payment_id',
        'invoice_id',
        string='Mobilvendor Invoices',
        domain=[('move_type', '=', 'out_invoice')],
        help='Invoices related to this payment from Mobilvendor'
    )

    mobilvendor_route_id = fields.Many2one(
        'mobilvendor.route',
        string='Collection Route',
        index=True
    )

    def action_post(self):
        """
        Override action_post method to:
        1. Reconcile GROUPED Mobilvendor invoices using specific amounts from context.
        2. Send balance updates to API for ALL invoices.
        """
        res = super(AccountPayment, self).action_post()

        records_to_send_api = []
        company_for_api = None

        # RETRIEVE SPECIFIC BREAKDOWN FROM CONTEXT
        # This prevents Odoo from swallowing the whole payment in a single invoice
        reconciliation_breakdown = self.env.context.get('mv_reconciliation_breakdown', {})

        for payment in self:
            if not payment.mobilvendor_id:
                continue

            invoices = payment.mobilvendor_invoice_ids

            if not invoices:
                _logger.warning(f"Payment {payment.mobilvendor_id} has no related invoices")
                continue

            if not company_for_api:
                company_for_api = payment.company_id or self.env.company

            # ================================================================
            # RECONCILIATION: For EACH related invoice
            # ================================================================
            reconciled_invoices = self.env['account.move']

            for invoice in invoices:
                try:
                    reconciled_invoice_line = invoice.line_ids.filtered(
                        lambda x: x.account_id.account_type == 'asset_receivable'
                                  and not x.reconciled
                    )

                    payment.move_id.line_ids.invalidate_recordset(['reconciled', 'amount_residual'])
                    reconciled_payment_line = payment.move_id.line_ids.filtered(
                        lambda x: x.account_id.account_type == 'asset_receivable'
                                  and not x.reconciled
                    )

                    if reconciled_invoice_line and reconciled_payment_line:
                        # Check for specific amount in context for this invoice
                        exact_amount = reconciliation_breakdown.get(invoice.id)

                        if exact_amount is not None and exact_amount > 0:
                            # FORCED PARTIAL RECONCILIATION
                            # We create the record manually to protect the remaining payment balance.
                            # No sudo() — cron runs as admin; keeping the same env ensures ORM
                            # triggers fire in one queue, preventing stale recomputation overwrites.
                            self.env['account.partial.reconcile'].create({
                                'debit_move_id': reconciled_invoice_line[
                                    0].id if invoice.move_type == 'out_invoice' else reconciled_payment_line[0].id,
                                'credit_move_id': reconciled_payment_line[
                                    0].id if invoice.move_type == 'out_invoice' else reconciled_invoice_line[0].id,
                                'amount': exact_amount,
                                'debit_amount_currency': exact_amount,
                                'credit_amount_currency': exact_amount,
                            })
                            reconciled_invoices |= invoice
                        else:
                            # No valid breakdown amount — skip to avoid consuming the full
                            # payment balance against a single invoice in multi-invoice payments
                            _logger.warning(
                                f"Payment {payment.mobilvendor_id} - No breakdown amount for "
                                f"invoice {invoice.name}, skipping reconciliation."
                            )
                            continue

                        _logger.info(
                            f"Payment {payment.mobilvendor_id} reconciled with invoice {invoice.name}"
                        )
                    else:
                        _logger.warning(
                            f"Payment {payment.mobilvendor_id} - No lines to reconcile for invoice {invoice.name}"
                        )
                        continue

                except Exception as e:
                    _logger.error(
                        f"Error reconciling payment {payment.mobilvendor_id} "
                        f"with invoice {invoice.name}: {e}"
                    )
                    continue

                # ============================================================
                # PREPARE PAYLOAD FOR API
                # ============================================================
                customer = invoice.partner_id
                customer_code = customer.mobilvendor_id if customer.mobilvendor_id else str(customer.id)

                payload = {
                    'code': invoice.mobilvendor_id,
                    'doc': invoice.name,
                    'comment': invoice.invoice_partner_display_name,
                    'customer_code': customer_code,
                    'create_date': invoice.date.strftime('%Y-%m-%d') if invoice.date else datetime.now().strftime(
                        '%Y-%m-%d'),
                    'expire_date': invoice.invoice_date_due.strftime(
                        '%Y-%m-%d') if invoice.invoice_date_due else datetime.now().strftime('%Y-%m-%d'),
                    'subtotal': invoice.amount_untaxed,
                    'taxes': invoice.amount_tax,
                    'amount': invoice.amount_total,
                    'balance': invoice.amount_residual,
                }
                records_to_send_api.append(payload)

            # Fix payment_state for reconciled invoices.
            # The localization module keeps is_matched=False on payments (custom
            # 'in_process' state), so _compute_payment_state() always returns
            # 'in_payment' even when amount_residual is 0. We flush all pending
            # ORM recomputes first, then override via SQL for invoices confirmed
            # as fully or partially paid. No dependency changes occur after this
            # point so no ORM recompute will override the values.
            if reconciled_invoices:
                self.env.flush_all()
                reconciled_invoices.invalidate_recordset(['amount_residual'])
                fully_paid_ids = [
                    inv.id for inv in reconciled_invoices if inv.amount_residual == 0
                ]
                partial_ids = [
                    inv.id for inv in reconciled_invoices
                    if 0 < inv.amount_residual < inv.amount_total
                ]
                if fully_paid_ids:
                    self.env.cr.execute(
                        "UPDATE account_move SET payment_state = 'paid' WHERE id IN %s",
                        (tuple(fully_paid_ids),)
                    )
                if partial_ids:
                    self.env.cr.execute(
                        "UPDATE account_move SET payment_state = 'partial' WHERE id IN %s",
                        (tuple(partial_ids),)
                    )
                reconciled_invoices.invalidate_recordset(['payment_state'])
                _logger.info(
                    f"Payment {payment.mobilvendor_id}: set payment_state for "
                    f"{len(fully_paid_ids)} paid, {len(partial_ids)} partial invoices."
                )

        # ====================================================================
        # SEND UPDATES TO API
        # ====================================================================
        if records_to_send_api:
            _logger.info(f"Sending {len(records_to_send_api)} balance updates to Mobilvendor.")
            try:
                api_handler = MobilvendorAPIHandler(company=company_for_api, env=self.env)
                api_handler.mobilvendor_send_balance_debit(records=records_to_send_api)
                _logger.info(f"Updates successfully sent to Mobilvendor")
            except Exception as e:
                _logger.error(f"Error sending updates to Mobilvendor: {e}")

        return res