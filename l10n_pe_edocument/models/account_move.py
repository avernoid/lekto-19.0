from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_repr, float_round

REFUND_REASON_13 = ('13', 'Correction of the net amount pending payment and/or due dates')
ACCOUNT_DETRACTION_VALIDATION_ERROR = ("Operación sujeta a detracción que supera la cantidad, debe indicar en el campo \"operation type\" que es afecta a "
                                       "detracción, por lo que la factura no puede ser publicada hasta que arregle el error.")


class AccountMove(models.Model):
    _inherit = 'account.move'

    payment_method_id = fields.Many2one(
        comodel_name='payment.methods.codes',
        string='Payment Method',
        help='Indicates the payment method used for this transaction, required for electronic invoicing.'
    )
    l10n_pe_edi_refund_reason = fields.Selection(selection_add=[REFUND_REASON_13])
    related_tax_documents_code = fields.Selection(
        selection=[
            ('01', 'Factura - emitida para corregir error en el RUC'),
            ('02', 'Factura - emitida por anticipos'),
            ('03', 'Boleta de venta - Emitida por anticipos'),
            ('04', 'Ticket de salida - ENAPU'),
            ('05', 'Código SCOP'),
            ('06', 'Factura electrónica remitente'),
            ('07', 'Guía de remisión remitente'),
            ('08', 'Declaración de salida del depósito franco'),
            ('09', 'Declaración simplificada de importación'),
            ('10', 'Liquidación de compra - emitida por anticipos'),
            ('99', 'Otros'),
        ],
        string='Related Tax Document Code',
        help='Code of the related tax document, used for specific SUNAT operations like debit notes or rectifications.'
    )

    @api.onchange('l10n_pe_edi_operation_type')
    def _onchange_payment_method(self):
        transfer_funds = self.env['payment.methods.codes'].search([('code', '=', '003')], limit=1)
        if self.l10n_pe_edi_operation_type in ['1001', '1002', '1003', '1004'] and any(transfer_funds):
            self.payment_method_id = transfer_funds.id
        else:
            self.payment_method_id = None

    def action_post(self):
        peru_id = self.env.ref('base.pe')
        payment_means_codes = {'1001', '1002', '1003', '1004'}
        exportation_codes = {'0201', '0202', '0203', '0204', '0205', '0206', '0207', '0208'}

        for move in self:
            max_percent = any(move.invoice_line_ids.mapped('product_id.l10n_pe_withhold_code'))
            is_detraction = any(move.invoice_payment_term_id.line_ids.mapped('l10n_pe_is_detraction_retention'))
            detraction_operation_type = move.l10n_pe_edi_operation_type in payment_means_codes or \
                                        move.l10n_pe_edi_operation_type in exportation_codes

            if (
                    move.l10n_latam_document_type_id and
                    move.l10n_latam_document_type_id.code == '01' and
                    peru_id == move.env.company.country_id and
                    (max_percent or is_detraction) and
                    (move.amount_total_signed >= 700 and not detraction_operation_type) and
                    move.journal_id.type == 'sale' and
                    move.journal_id.l10n_latam_use_documents
            ):
                raise UserError(ACCOUNT_DETRACTION_VALIDATION_ERROR)
        return super(AccountMove, self).action_post()

    def _l10n_pe_edi_get_spot(self):
        spot = super(AccountMove, self)._l10n_pe_edi_get_spot()
        if spot:
            spot.update({'payment_means_code': self.payment_method_id.code})
        return spot

    @api.model_create_multi
    def create(self, values):
        for value in values:
            if value.get('l10n_pe_edi_refund_reason') and not value.get('l10n_pe_edi_cancel_reason') and value.get('ref'):
                value['l10n_pe_edi_cancel_reason'] = value['ref']
        return super().create(values)
