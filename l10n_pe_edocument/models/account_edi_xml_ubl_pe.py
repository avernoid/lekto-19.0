from odoo import models
from odoo.exceptions import UserError
from odoo.addons.l10n_pe_edi.models.account_edi_xml_ubl_pe import FREE_AFFECTATION_REASONS
from unicodedata import normalize, combining


class AccountEdiXmlUBLPE(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_pe'

    def _l10n_pe_edi_get_formatted_order_reference(self, value):
        """
            <f2> Referencia de cliente
            Formatea la referencia del pedido eliminando caracteres especiales y diacríticos,
            y limitando la longitud a 20 caracteres.
        """
        order_reference = (value or '').strip()
        if not order_reference:
            return order_reference[:20]

        normalized = normalize('NFKD', order_reference)
        without_diacritics = ''.join(ch for ch in normalized if not combining(ch))

        special_characters = "¿?|°<>[]/'@!¡#$%^&*()´+\t.,:;\n "
        for char in special_characters:
            without_diacritics = without_diacritics.replace(char, '')

        cleaned = ''.join(ch for ch in without_diacritics if ch.isalnum())

        return cleaned[:20]

    def _add_invoice_header_nodes(self, document_node, vals):
        super()._add_invoice_header_nodes(document_node, vals)

        invoice = vals['invoice']
        # <f2> Referencia de cliente
        order_reference = self._l10n_pe_edi_get_formatted_order_reference(document_node['cac:OrderReference']['cbc:ID']['_text'])
        document_node['cac:OrderReference']['cbc:ID']['_text'] = order_reference

        # <f7> Guía de Remisión
        if invoice.carrier_ref_number:
            document_node['cac:DespatchDocumentReference'] = {
                'cbc:ID': {'_text': str(invoice.carrier_ref_number).replace('\n', '').replace(' ', '')[:30]},
                'cbc:DocumentTypeCode': {'_text': '09' , 'listAgencyName': 'PE:SUNAT', 'listName': 'Tipo de Documento',
                                         'listURI': 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo01'},
            }
        # <f8> Otros tipos doc.
        if invoice.aditional_document_reference:
            document_node['cac:AdditionalDocumentReference'] = {
                'cbc:ID': {'_text': str(invoice.aditional_document_reference).replace('\n', '').replace(' ', '')[:30]},
                'cbc:DocumentTypeCode': {'_text': invoice.related_tax_documents_code, 'listAgencyName': 'PE:SUNAT', 'listName': 'Documento Relacionado',
                                         'listURI': 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo12'},
            }

    def _add_invoice_monetary_total_nodes(self, document_node, vals):
        super()._add_invoice_monetary_total_nodes(document_node, vals)

        monetary_total_tag = 'cac:LegalMonetaryTotal' if vals['document_type'] in {'invoice', 'credit_note'} else 'cac:RequestedMonetaryTotal'
        monetary_total_node = document_node[monetary_total_tag]
        invoice = vals['invoice']
        line_extension_amount = monetary_total_node['cbc:LineExtensionAmount']['_text']
        tax_exclusive_amount = monetary_total_node['cbc:TaxExclusiveAmount']['_text']
        tax_inclusive_amount = monetary_total_node['cbc:TaxInclusiveAmount']['_text']
        payable_amount = monetary_total_node['cbc:PayableAmount']['_text']

        # print('cbc:LineExtensionAmount')
        # print(line_extension_amount)
        # print('tax_exclusive_amount')
        # print(tax_exclusive_amount)
        # print('tax_inclusive_amount')
        # print(tax_inclusive_amount)
        # print('PayableAmount')
        # print(payable_amount)

        # Actualizar totales cuando hay impuestos especiales:
        for line_idx, base_line in enumerate(vals['base_lines']):
            # print(base_line)
            line_vals = {
                **vals,
                'line_idx': line_idx,
                'base_line': base_line,
            }
            line_node = self._get_invoice_line_node(line_vals)
            for tax_line in line_node['cac:TaxTotal']['cac:TaxSubtotal']:
                tax_category = tax_line['cac:TaxCategory']

                # print('tax_category')
                # print(tax_category)
                # print(tax_category['cac:TaxScheme']['cbc:ID']['_text'])
                # print(tax_category['cac:TaxScheme']['cbc:Name']['_text'])
                # print(tax_category['cac:TaxScheme']['cbc:TaxTypeCode']['_text'])
                # print(tax_category['cbc:TaxExemptionReasonCode']['_text'])
                # <f10> Múltiples impuestos
                #  - Ejemplo 1: IGV/ 18% Libre (Nativo)
                if tax_category['cac:TaxScheme']['cbc:ID']['_text'] == '9996' and tax_category['cac:TaxScheme']['cbc:Name']['_text'] == 'GRA' and \
                        tax_category['cac:TaxScheme']['cbc:TaxTypeCode']['_text'] == 'FRE' and tax_category['cbc:TaxExemptionReasonCode']['_text'] == '11':
                    line_extension_amount += line_node['cbc:LineExtensionAmount']['_text']
                    tax_exclusive_amount -= line_node['cbc:LineExtensionAmount']['_text']
                    tax_inclusive_amount += tax_line['cbc:TaxableAmount']['_text'] + tax_line['cbc:TaxAmount']['_text']
                # <f3> Retiro por bonificación
                elif tax_category['cac:TaxScheme']['cbc:ID']['_text'] == '9996' and tax_category['cac:TaxScheme']['cbc:Name']['_text'] == 'GRA' and \
                    tax_category['cac:TaxScheme']['cbc:TaxTypeCode']['_text'] == 'FRE' and tax_category['cbc:TaxExemptionReasonCode']['_text'] == '31':
                    # print('entre')
                    line_extension_amount -= line_node['cbc:LineExtensionAmount']['_text']
                    tax_exclusive_amount -= line_node['cbc:LineExtensionAmount']['_text']
                    tax_inclusive_amount -= tax_line['cbc:TaxableAmount']['_text']
                    payable_amount -= tax_line['cbc:TaxableAmount']['_text']

        monetary_total_node['cbc:LineExtensionAmount']['_text'] = self.format_float(line_extension_amount, vals['currency_dp'])
        monetary_total_node['cbc:TaxExclusiveAmount']['_text'] = self.format_float(tax_exclusive_amount, vals['currency_dp'])
        monetary_total_node['cbc:TaxInclusiveAmount']['_text'] = self.format_float(tax_inclusive_amount, vals['currency_dp'])
        monetary_total_node['cbc:PayableAmount']['_text'] = self.format_float(payable_amount, vals['currency_dp'])

        # Credit note - code 13
        if invoice.l10n_pe_edi_refund_reason == '13':
            monetary_total_node['cbc:LineExtensionAmount']['_text'] = self.format_float(0.0, vals['currency_dp'])
            monetary_total_node['cbc:TaxExclusiveAmount']['_text'] = self.format_float(0.0, vals['currency_dp'])
            monetary_total_node['cbc:TaxInclusiveAmount']['_text'] = self.format_float(0.0, vals['currency_dp'])
            monetary_total_node['cbc:PayableAmount']['_text'] = self.format_float(0.0, vals['currency_dp'])

    def _add_invoice_payment_terms_nodes(self, document_node, vals):
        """
            OVERRIDE l10n_pe_edi
            <f4> Nota de crédito tipo 13
            Modifica terminos de pagos para que soporte:
             - Retenciones: Calculos de las cuotas de pago
             - Nota de credito: Codigo 13
        """
        invoice = vals['invoice']
        spot = invoice._l10n_pe_edi_get_spot()
        invoice_date_due_vals_list = []
        for rec_line in invoice.line_ids.filtered(lambda l: l.account_type == 'asset_receivable' and not l.l10n_pe_is_detraction_retention):
            invoice_date_due_vals_list.append({
                'currency_name': rec_line.currency_id.name,
                'currency_dp': rec_line.currency_id.decimal_places,
                'amount': abs(rec_line.amount_currency),
                'date_maturity': rec_line.date_maturity,
            })

        total_after_spot = sum(due_vals['amount'] for due_vals in invoice_date_due_vals_list)
        payment_means_id = invoice._l10n_pe_edi_get_payment_means()
        payment_terms = []
        if spot:
            payment_terms.append({
                'cbc:ID': {'_text': spot['id']},
                'cbc:PaymentMeansID': {'_text': spot['payment_means_id']},
                'cbc:PaymentPercent': {'_text': spot['payment_percent']},
                'cbc:Amount': {
                    '_text': self.format_float(spot['amount'], 2),
                    'currencyID': 'PEN'
                },
            })
        if (invoice.l10n_pe_edi_refund_reason == '13' and invoice.move_type == 'out_refund') or invoice.move_type not in ('out_refund', 'in_refund'):
            if payment_means_id == 'Contado':
                payment_terms.append({
                    'cbc:ID': {'_text': 'FormaPago'},
                    'cbc:PaymentMeansID': {'_text': payment_means_id}
                })
            else:
                payment_terms.append({
                    'cbc:ID': {'_text': 'FormaPago'},
                    'cbc:PaymentMeansID': {'_text': payment_means_id},
                    'cbc:Amount': {
                        '_text': self.format_float(total_after_spot, invoice.currency_id.decimal_places),
                        'currencyID': invoice.currency_id.name
                    }
                })
                for i, due_vals in enumerate(invoice_date_due_vals_list):
                    amount = abs(due_vals['amount']) if invoice.l10n_pe_edi_refund_reason == '13' else due_vals['amount']
                    payment_terms.append({
                        'cbc:ID': {'_text': 'FormaPago'},
                        'cbc:PaymentMeansID': {'_text': f'Cuota{(i + 1):03d}'},
                        'cbc:Amount': {
                            '_text': self.format_float(amount, due_vals['currency_dp']),
                            'currencyID': due_vals['currency_name']
                        },
                        'cbc:PaymentDueDate': {'_text': due_vals['date_maturity']}
                    })
        document_node['cac:PaymentTerms'] = payment_terms

    def _add_invoice_tax_total_nodes(self, document_node, vals):
        super()._add_invoice_tax_total_nodes(document_node, vals)
        invoice = vals['invoice']

        # <f10> Múltiples impuestos: Reemplaza el calculo del TaxTotal/TaxAmount para soportar multiples impuestos por linea
        tax_amount = 0.0
        for tax in document_node['cac:TaxTotal']['cac:TaxSubtotal']:
            if tax['cac:TaxCategory']['cac:TaxScheme']['cbc:ID']['_text'] in ['1000', '1016', '2000', '7152', '9999']:
                tax_amount += tax['cbc:TaxAmount']['_text']
        document_node['cac:TaxTotal']['cbc:TaxAmount']['_text'] = self.format_float(tax_amount, vals['currency_dp'])

        # Credit note - code 13
        if invoice.l10n_pe_edi_refund_reason == '13':
            document_node['cac:TaxTotal']['cbc:TaxAmount']['_text'] = self.format_float(0.0, vals['currency_dp'])
            for tax in document_node['cac:TaxTotal']['cac:TaxSubtotal']:
                tax['cbc:TaxableAmount']['_text'] = self.format_float(0.0, vals['currency_dp'])
                tax['cbc:TaxAmount']['_text'] = self.format_float(0.0, vals['currency_dp'])

    def _get_invoice_line_node(self, vals):
        line_node = super()._get_invoice_line_node(vals)
        invoice = vals['invoice']
        # Credit note - code 13
        if invoice.l10n_pe_edi_refund_reason == '13':
            line_node['cbc:LineExtensionAmount']['_text'] = self.format_float(0.0, vals['currency_dp'])
            line_node['cac:PricingReference']['cac:AlternativeConditionPrice']['cbc:PriceAmount']['_text'] = self.format_float(0.0, vals['currency_dp'])
            line_node['cac:TaxTotal']['cbc:TaxAmount']['_text'] = self.format_float(0.0, vals['currency_dp'])
            line_node['cac:Price']['cbc:PriceAmount']['_text'] = self.format_float(0.0, vals['currency_dp'])
            for line_tax in line_node['cac:TaxTotal']['cac:TaxSubtotal']:
                line_tax['cbc:TaxableAmount']['_text'] = self.format_float(0.0, vals['currency_dp'])
                line_tax['cbc:TaxAmount']['_text'] = self.format_float(0.0, vals['currency_dp'])
        return line_node

    def _add_invoice_line_nodes(self, document_node, vals):
        """
            <f11> Zero line
             Consider lines whose line_price_subtotal is greater than 0
        """
        invoice = vals['invoice']
        if not (vals['document_type'] == 'credit_note' and invoice.l10n_latam_document_type_id.code == '07' and invoice.l10n_pe_edi_refund_reason == '03'):
            vals['base_lines'] = [
                line
                for line in vals['base_lines']
                if float(line['record'].price_subtotal) > 0
            ]
        super()._add_invoice_line_nodes(document_node, vals)

    # def _get_invoice_line_vals(self, line, line_id, taxes_vals):
    #     vals = super()._get_invoice_line_vals(line, line_id, taxes_vals)
    #
    #     # Credit note - code 13
    #     if line.move_id.l10n_pe_edi_refund_reason == '13':
    #         vals['pricing_reference_vals']['alternative_condition_price_vals'][0]['price_amount'] = 0
    #         vals['line_extension_amount'] = 0
    #
    #     # Add line_price_subtotal to avoid line price subtotal being 0
    #     vals['line_price_subtotal'] = line.price_subtotal
    #
    #     # Remove ICBPER tax from the line_extension_amount line
    #     for tax_line in vals['tax_total_vals'][0]['tax_subtotal_vals']:
    #         if tax_line['tax_category_vals']['tax_scheme_vals']['id'] == '7152':
    #             vals['line_extension_amount'] -= tax_line['tax_amount'] if vals['line_extension_amount'] > tax_line['tax_amount'] else 0.0
    #             vals['allowance_charge_vals'] = []
    #     return vals

    # def _get_invoice_monetary_total_vals(self, invoice, taxes_vals, line_extension_amount, allowance_total_amount, charge_total_amount):
    #     vals = super()._get_invoice_monetary_total_vals(invoice, taxes_vals, line_extension_amount, allowance_total_amount, charge_total_amount)
    #
    #     # Recalcula usando como base el metodo original definido en el modulo account_edi_ubl_cii/account_edi_xml_ubl_20.py
    #     line_extension_amount = line_extension_amount
    #     tax_exclusive_amount = taxes_vals['base_amount_currency']
    #     tax_inclusive_amount = invoice.amount_total
    #     payable_amount = invoice.amount_total
    #
    #     invoice_lines = invoice.invoice_line_ids.filtered(lambda x: x.display_type not in ('line_note', 'line_section'))
    #     # Actualizar totales cuando hay impuestos especiales:
    #     for line_id, line in enumerate(invoice_lines):
    #         if self._check_line_withdrawal_tax(line) or self._check_line_unaffected_tax(line):
    #             line_taxes_vals = taxes_vals['tax_details_per_record'][line]
    #             line_vals = self._get_invoice_line_vals(line, line_id, {**line_taxes_vals, 'invoice_line': line})
    #
    #             line_extension_amount -= abs(line_vals['line_extension_amount'])
    #             tax_exclusive_amount -= abs(line_taxes_vals['base_amount_currency'])
    #             for tax_line in line_vals['tax_total_vals'][0]['tax_subtotal_vals']:
    #                 # - 0% Obsequio - Retiro por bonificación
    #                 print(tax_line['tax_category_vals'])
    #                 if tax_line['tax_category_vals']['tax_scheme_vals']['id'] == '9996' and tax_line['tax_category_vals']['tax_exemption_reason_code'] == '31':
    #                     tax_inclusive_amount -= abs(line.amount_currency)
    #                     payable_amount -= abs(line.amount_currency)
    #
    #     vals.update({
    #         'line_extension_amount': line_extension_amount if line_extension_amount > 0 else 0,
    #         'tax_exclusive_amount': tax_exclusive_amount if tax_exclusive_amount > 0 else 0,
    #         'tax_inclusive_amount': tax_inclusive_amount if tax_inclusive_amount > 0 else 0,
    #         'payable_amount': payable_amount if payable_amount > 0 else 0,
    #     })
    #     # Credit note - code 13
    #     if invoice.l10n_pe_edi_refund_reason == '13':
    #         vals.update({
    #             'line_extension_amount': 0,
    #             'tax_exclusive_amount': 0,
    #             'tax_inclusive_amount': 0,
    #             'allowance_total_amount': 0,
    #             'payable_amount': 0,
    #         })
    #     return vals

    # def _export_invoice_vals(self, invoice):
    #     vals = super()._export_invoice_vals(invoice)
    #
    #     vals['vals'].update({'order_reference': self._l10n_pe_edi_get_order_reference(invoice)})
    #
    #     # Credit Note specific changes
    #     if vals['document_type'] == 'credit_note':
    #         if invoice.l10n_latam_document_type_id.code == '07':
    #             if 'discrepancy_response_vals' in vals['vals']:
    #                 vals['vals']['discrepancy_response_vals'][0]['description'] = invoice.l10n_pe_edi_cancel_reason
    #         if invoice.origin_number and invoice.origin_l10n_latam_document_type_id:
    #             vals['vals'].update({
    #                 'billing_reference_vals': {
    #                     'id': invoice.origin_number.replace(' ', ''),
    #                     'document_type_code': invoice.origin_l10n_latam_document_type_id.code,
    #                 },
    #             })
    #
    #     # Debit Note specific changes
    #     if vals['document_type'] == 'debit_note':
    #         if invoice.l10n_latam_document_type_id.code == '08':
    #             if 'discrepancy_response_vals' in vals['vals']:
    #                 vals['vals']['discrepancy_response_vals'][0]['description'] = invoice.l10n_pe_edi_cancel_reason
    #         if invoice.origin_number and invoice.origin_l10n_latam_document_type_id:
    #             vals['vals'].update({
    #                 'billing_reference_vals': {
    #                     'id': invoice.origin_number.replace(' ', ''),
    #                     'document_type_code': invoice.origin_l10n_latam_document_type_id.code,
    #                 },
    #             })
    #
    #     if invoice.carrier_ref_number:
    #         vals['vals'].update({
    #             'despatch_document_reference': str(invoice.carrier_ref_number).replace('\n', '').replace(' ', '')[:30],
    #             'despatch_document_reference_type_code': '09',
    #         })
    #
    #     if invoice.aditional_document_reference:
    #         vals['vals'].update({
    #             'additional_document_reference': str(invoice.aditional_document_reference).replace('\n', '').replace(' ', '')[:30],
    #             'additional_document_reference_type_code': invoice.related_tax_documents_code or '',
    #         })
    #
    #     if invoice.agent_retention:
    #         vals['vals']['allowance_charge_vals'] = [{
    #             'retention_invoice': True,
    #             'charge_indicator': 'false',
    #             'allowance_charge_reason_code': '62',
    #             'multiplier_factor': invoice.multiplier_factor_field,
    #             'amount': float(invoice.amount_field_advance),
    #             'base_amount': float(invoice.debit_field_advance),
    #             'currency_dp': 2,
    #             'currency_name': invoice.currency_id.name
    #         }]
    #
    #     # Consider lines whose line_price_subtotal is greater than 0
    #     if not (vals['document_type'] == 'credit_note' and invoice.l10n_latam_document_type_id.code == '07' and invoice.l10n_pe_edi_refund_reason == '03'):
    #         vals['vals']['line_vals'] = [
    #             line
    #             for line in vals['vals']['line_vals']
    #             if float(line['line_price_subtotal']) > 0
    #         ]
    #     return vals

    # def _get_partner_party_legal_entity_vals_list(self, partner):
    #     vals = super()._get_partner_party_legal_entity_vals_list(partner)
    #     for val in vals:
    #         registration_name = partner.name
    #         if partner and partner.name and partner.parent_id and partner.parent_id.name:
    #             registration_name += ', ' + partner.parent_id.name
    #         val.update({'registration_name': registration_name})
    #     return vals
    #


    #
    # def _get_invoice_tax_totals_vals_list(self, invoice, taxes_vals):
    #     tax_subtotal_vals = super()._get_invoice_tax_totals_vals_list(invoice, taxes_vals)
    #
    #     # Reemplaza el calculo del TaxTotal/TaxAmount para soportar multiples impuestos por linea
    #     tax_amount = 0.00
    #     for taxes_vals in tax_subtotal_vals[0]['tax_subtotal_vals']:
    #         if taxes_vals['tax_category_vals']['tax_scheme_vals']['id'] in ['1000', '1016', '2000', '7152', '9999']:
    #             # Elimina tag TaxableAmount para impuesto ICBPER
    #             if taxes_vals['tax_category_vals']['tax_scheme_vals']['id'] == '7152':
    #                 del taxes_vals['taxable_amount']
    #             tax_amount += taxes_vals['tax_amount']
    #     tax_subtotal_vals[0]['tax_amount'] = tax_amount
    #
    #     # Credit note - code 13
    #     if invoice.l10n_pe_edi_refund_reason == '13':
    #         for tax in [tax_val for tax_val in tax_subtotal_vals[0]['tax_subtotal_vals']]:
    #             tax_subtotal_vals[0]['tax_amount'] = 0
    #             tax['taxable_amount'] = 0
    #             tax['tax_amount'] = 0
    #     return tax_subtotal_vals
    #

    #
    # def _get_invoice_line_price_vals(self, line):
    #     """
    #         Credit note - code 13
    #     """
    #     vals = super()._get_invoice_line_price_vals(line)
    #
    #     price_precision = self.env['decimal.precision'].precision_get('Product Price')
    #     is_line_withdrawal_tax = self._check_line_withdrawal_tax(line)
    #     is_line_unaffected_tax = self._check_line_unaffected_tax(line)
    #
    #     if is_line_withdrawal_tax or is_line_unaffected_tax or line.move_id.l10n_pe_edi_refund_reason == '13':
    #         vals.update({'price_amount': float(self.format_float(0, price_precision))})
    #     return vals
    #
    # def _get_invoice_line_vals(self, line, line_id, taxes_vals):
    #     vals = super()._get_invoice_line_vals(line, line_id, taxes_vals)
    #
    #     # Credit note - code 13
    #     if line.move_id.l10n_pe_edi_refund_reason == '13':
    #         vals['pricing_reference_vals']['alternative_condition_price_vals'][0]['price_amount'] = 0
    #         vals['line_extension_amount'] = 0
    #
    #     # Add line_price_subtotal to avoid line price subtotal being 0
    #     vals['line_price_subtotal'] = line.price_subtotal
    #
    #     # Remove ICBPER tax from the line_extension_amount line
    #     for tax_line in vals['tax_total_vals'][0]['tax_subtotal_vals']:
    #         if tax_line['tax_category_vals']['tax_scheme_vals']['id'] == '7152':
    #             vals['line_extension_amount'] -= tax_line['tax_amount'] if vals['line_extension_amount'] > tax_line['tax_amount'] else 0.0
    #             vals['allowance_charge_vals'] = []
    #     return vals
    #
    # def _get_invoice_line_tax_totals_vals_list(self, line, taxes_vals):
    #     # OVERRIDE l10n_pe_edi
    #     vals = {
    #         'currency': line.currency_id,
    #         'currency_dp': line.currency_id.decimal_places,
    #         'tax_amount': 0.00 if line.l10n_pe_edi_affectation_reason in FREE_AFFECTATION_REASONS else line.price_total - line.price_subtotal,
    #         'tax_subtotal_vals': [],
    #     }
    #
    #     for tax_detail_vals in taxes_vals['tax_details'].values():
    #         tax = tax_detail_vals['taxes_data'][0]['tax']
    #         if tax_detail_vals['tax_amount_currency'] < 0 and line.move_id.l10n_pe_edi_legend == '1002':
    #             continue
    #         if tax.tax_group_id.l10n_pe_edi_code == 'ICBPER':
    #             percent = 0.0
    #         elif tax.amount_type == 'percent':
    #             percent = tax.amount
    #         else:
    #             percent = None,
    #         vals['tax_subtotal_vals'].append({
    #             'currency': line.currency_id,
    #             'currency_dp': line.currency_id.decimal_places,
    #             'taxable_amount': tax_detail_vals['base_amount_currency'] if tax.tax_group_id.l10n_pe_edi_code != 'ICBPER' else None,
    #             'tax_amount': tax_detail_vals['tax_amount_currency'] or 0.0,
    #             'base_unit_measure_attrs': {
    #                 'unitCode': 'NIU' if line._get_downpayment_lines() else line.product_uom_id.l10n_pe_edi_measure_unit_code,
    #             },
    #             'base_unit_measure': int(line.quantity) if tax.tax_group_id.l10n_pe_edi_code == 'ICBPER' else None,
    #             'tax_category_vals': {
    #                 # Modify this lines to be used by ICBPER tax
    #                 'currency_name': line.currency_id.name,
    #                 'percent': percent,
    #                 'per_unit_amount': tax.amount or 0.0 if tax.tax_group_id.l10n_pe_edi_code == 'ICBPER' else None,
    #                 # Modify the tax_exemption_reason_code validation over ICBPER tax and
    #                 # validate directly over the tax and not the line because line always work with the first tax
    #                 'tax_exemption_reason_code': (
    #                     tax.l10n_pe_edi_affectation_reason
    #                     if tax.tax_group_id.l10n_pe_edi_code not in ['ICBPER'] and tax.l10n_pe_edi_affectation_reason else None
    #                 ),
    #                 'tier_range': tax.l10n_pe_edi_isc_type if tax.tax_group_id.l10n_pe_edi_code == 'ISC' and tax.l10n_pe_edi_isc_type else None,
    #                 'tax_scheme_vals': {
    #                     'id': tax.l10n_pe_edi_tax_code,
    #                     'name': tax.tax_group_id.l10n_pe_edi_code,
    #                     'tax_type_code': tax.l10n_pe_edi_international_code,
    #                 },
    #             },
    #         })
    #     tax_vals = vals
    #     tax_subtotal_vals = tax_vals.get('tax_subtotal_vals', [{}])
    #
    #     if not tax_subtotal_vals:
    #         tax_vals['tax_subtotal_vals'] = [{}]
    #         return [tax_vals]
    #
    #     # Credit note - code 13
    #     if line.move_id.l10n_pe_edi_refund_reason == '13':
    #         tax_vals['tax_amount'] = 0
    #         tax_subtotal_vals[0]['taxable_amount'] = 0
    #         tax_subtotal_vals[0]['tax_amount'] = 0
    #
    #     return [tax_vals]
    #
    # @staticmethod
    # def _check_line_withdrawal_tax(line):
    #     conditions = (
    #         line.move_id.move_type in ('out_invoice', 'out_refund'),
    #         line.move_id.country_code == 'PE',
    #         line.l10n_pe_edi_affectation_reason in ('11', '12', '13', '14', '15', '16')
    #     )
    #     return all(conditions)
    #
    # @staticmethod
    # def _check_line_unaffected_tax(line):
    #     conditions = (
    #         line.move_id.move_type in ('out_invoice', 'out_refund'),
    #         line.move_id.country_code == 'PE',
    #         line.l10n_pe_edi_affectation_reason in ('21', '31', '32', '33', '34', '35', '36', '37')
    #     )
    #     return all(conditions)
