from odoo import Command
from odoo.tests import tagged, Form
from odoo.addons.l10n_pe_edi.tests.common import mocked_l10n_pe_edi_post_invoice_web_service
from .common import TestL10nPeEdocument
from unittest.mock import patch
from freezegun import freeze_time
import odoo.modules


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestRectifyingXmls(TestL10nPeEdocument):

    def setUp(self):
        super(TestRectifyingXmls, self).setUp()
        self.error_label = "l10n_pe_edocument - Retención:"
        self.l10n_pe_edocument_expected_credit_note_igv_usd_tpl = self.l10n_pe_edocument_load_tpl("credit_note_igv_usd.xml")
        self.l10n_pe_edocument_expected_credit_note_igv_sol_tpl = self.l10n_pe_edocument_load_tpl("credit_note_igv_sol.xml")
        self.expected_credit_note_sol_tax_igv_with_zero_line_code_3_tpl = self.l10n_pe_edocument_load_tpl("credit_note_sol_tax_igv_with_zero_line_code_3.xml")

    def test_credit_note_igv_sol(self):
        """
            Funcionalidad:
            - <f4> Nota de crédito tipo 13
        """
        with (freeze_time(self.frozen_today), \
              patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                    new=mocked_l10n_pe_edi_post_invoice_web_service)):
            test_ref = 'Nota de credito soles- referencia'
            invoice_line_ids = [(0, 0, {
                'product_id': self.product.id,
                'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                'price_unit': 1694.92,
                'quantity': 1,
                'tax_ids': [(6, 0, self.tax_18.ids)],
            })]
            origin_move = self._create_invoice(
                ref=test_ref,
                partner_id=self.l10n_pe_partner_ruc.id,
                currency_id=self.currency_sol.id,
                invoice_line_ids=invoice_line_ids,
                invoice_payment_term_id=self.thirty_days_payment_term_id.id
            )
            origin_move.action_post()

            context = {
                "active_model": 'account.move',
                "active_ids": [origin_move.id],
                "active_id": origin_move.id,
                'default_refund_method': 'refund',
            }
            with Form(self.env['account.move.reversal'].with_context(context)) as form:
                form.reason = 'Cancelar'
                form.l10n_pe_edi_refund_reason = '13'
                reversal_form = form.save()
                refund_invoice = self.env['account.move'].browse(reversal_form.refund_moves()['res_id'])

                self.assertEqual(
                    refund_invoice.l10n_pe_edi_cancel_reason,
                    f"Reversión de: {origin_move.name.replace(' ', '')}{f', {reversal_form.reason}' if reversal_form.reason else ''}",
                    f"{self.error_label} La nota de crédito no tiene la razón de cancelación correcta."
                )
                self.assertEqual(
                    refund_invoice.ref,
                    origin_move.ref,
                    f"{self.error_label} La nota de crédito no tiene la referencia correcta al documento original."
                )
                refund_invoice.invoice_payment_term_id = self.forty_five_days_payment_term_id.id
                refund_invoice.action_post()

                l10n_pe_edocument_expected_credit_note_igv_sol_xml = self.l10n_pe_edocument_expected_credit_note_igv_sol_tpl.format(
                    refund_number=refund_invoice.name.replace(' ', ''),
                    origin_number=origin_move.name.replace(' ', ''),
                    refund_reason='Nota de credito soles- referencia',
                    order_reference='Notadecreditosolesre',
                    party_legal_registration_name='hola'
                )
                self.l10n_pe_edocument_compare_expected_xmls(refund_invoice, l10n_pe_edocument_expected_credit_note_igv_sol_xml)

    def test_credit_note_sol_tax_igv_with_zero_line_code_3(self):
        """
            Funcionalidad:
            - <f11> Zero line - NC código 3
        """
        with (freeze_time(self.frozen_today), \
              patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                    new=mocked_l10n_pe_edi_post_invoice_web_service)):
            invoice_line_ids = [(0, 0, {
                'product_id': self.product.id,
                'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                'price_unit': 200.0,
                'quantity': 1,
                'tax_ids': [(6, 0, self.tax_18.ids)],
            })]
            origin_move = self._create_invoice(
                partner_id=self.l10n_pe_partner_ruc.id,
                currency_id=self.currency_sol.id,
                invoice_line_ids=invoice_line_ids
            )
            origin_move.action_post()

            context = {
                "active_model": 'account.move',
                "active_ids": [origin_move.id],
                "active_id": origin_move.id,
                'default_refund_method': 'refund',
            }
            with Form(self.env['account.move.reversal'].with_context(context)) as form:
                form.reason = 'Correción de error'
                form.l10n_pe_edi_refund_reason = '03'
                reversal_form = form.save()
                refund_invoice = self.env['account.move'].browse(reversal_form.refund_moves()['res_id'])

                self.assertEqual(
                    refund_invoice.l10n_pe_edi_cancel_reason,
                    f"Reversión de: {origin_move.name.replace(' ', '')}{f', {reversal_form.reason}' if reversal_form.reason else ''}",
                    f"{self.error_label} La nota de crédito no tiene la razón de cancelación correcta."
                )
                self.assertEqual(
                    refund_invoice.ref,
                    origin_move.ref,
                    f"{self.error_label} La nota de crédito no tiene la referencia correcta al documento original."
                )
                refund_invoice.invoice_line_ids[0].quantity = 1.0
                refund_invoice.invoice_line_ids[0].price_unit = 0.0
                refund_invoice.action_post()
                expected_credit_note_sol_tax_igv_with_zero_line_code_3_xml = self.expected_credit_note_sol_tax_igv_with_zero_line_code_3_tpl.format(
                    refund_number=refund_invoice.name.replace(' ', ''),
                    origin_number=origin_move.name.replace(' ', '')
                )
                self.l10n_pe_edocument_compare_expected_xmls(refund_invoice, expected_credit_note_sol_tax_igv_with_zero_line_code_3_xml)

    def l10n_pe_edocument_validate_order_reference_tag(self, invoice):
        etree = self.l10n_pe_edocument_get_etree_from_move(invoice)
        registration_name = self.xml_ubl_pe_model._get_partner_party_legal_entity_vals_list(self.l10n_pe_partner_ruc)[0]['registration_name']
        reference = self.xml_ubl_pe_model._l10n_pe_edi_get_order_reference(invoice)
        list_tags = [
            (".//{*}OrderReference//{*}ID", reference, f"{self.error_label} Etiqueta OrderReference erronea"),
            (".//{*}AccountingCustomerParty//{*}PartyLegalEntity//{*}RegistrationName", registration_name,
             f"{self.error_label} Etiqueta AccountingCustomerParty/PartyLegalEntity/RegistrationName erronea")
        ]
        self.l10n_pe_edocument_assert_xml_node(etree, list_tags)
