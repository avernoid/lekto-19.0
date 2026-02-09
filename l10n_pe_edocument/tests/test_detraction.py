from odoo import Command
from odoo.tests import tagged, Form
from odoo.addons.l10n_pe_edi.tests.common import mocked_l10n_pe_edi_post_invoice_web_service
from .common import TestL10nPeEdocument
from unittest.mock import patch
from freezegun import freeze_time
import odoo.modules
from odoo.exceptions import UserError
from ..models.account_move import ACCOUNT_DETRACTION_VALIDATION_ERROR


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPeDetraction(TestL10nPeEdocument):

    def setUp(self):
        super(TestL10nPeDetraction, self).setUp()
        self.error_label = "l10n_pe_edocument - Detraction:"
        self.l10n_pe_edocument_expected_invoice_igv_usd_detraction_tpl = self.l10n_pe_edocument_load_tpl('invoice_igv_usd_detraction.xml')

    def test_invoice_igv_usd_detraction(self):
        """
            Funcionalidad:
            - <f5> Medio de pago en detracción
            - <f7> Guía de Remisión
            - <f8> Otros tipos doc.
            - <f9> Acepta 3 Tag: Referencia cliente, Guía de remisión y Otro tipo de doc.
        """
        move_id = self.l10n_pe_edocument_create_invoice_detraction(payment_method_id=self.default_transfer_fund_id.id)
        with (freeze_time(self.frozen_today), patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                                                    new=mocked_l10n_pe_edi_post_invoice_web_service)):
            move_id.action_post()
            l10n_pe_edocument_expected_invoice_igv_usd_detraction_xml = self.l10n_pe_edocument_expected_invoice_igv_usd_detraction_tpl.format(
                additional_document_reference='F001-456512',
                additional_document_reference_type_code='99',
                carrier_ref_number='WH/OUT/00004'
            )
            self.l10n_pe_edocument_compare_expected_xmls(move_id, l10n_pe_edocument_expected_invoice_igv_usd_detraction_xml)
            self.l10n_pe_edocument_validate_detraction_tags(move_id)

    def test_invoice_igv_usd_detraction_force_error(self):
        """
            Funcionalidad:
            <f6> Alerta para detracción
        """
        move_id = self.l10n_pe_edocument_create_invoice_detraction(l10n_pe_edi_operation_type='0101', payment_method_id=False)
        with (freeze_time(self.frozen_today), patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                                                    new=mocked_l10n_pe_edi_post_invoice_web_service)):
            with self.assertRaisesRegex(UserError, ACCOUNT_DETRACTION_VALIDATION_ERROR):
                move_id.action_post()

    def l10n_pe_edocument_create_invoice_detraction(self, payment_method_id, l10n_pe_edi_operation_type='1001'):
        invoice_line_ids = [(0, 0, {
            'product_id': self.product_detraction.id,
            'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
            'price_unit': 163.2,
            'quantity': 14,
            'tax_ids': [(6, 0, self.tax_18.ids)],
        }), (0, 0, {
            'product_id': self.product.id,
            'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
            'price_unit': 0.04,
            'quantity': 2696.060,
            'tax_ids': [(6, 0, self.tax_18.ids)],
        })]
        move_id = self._create_invoice(
            invoice_line_ids=invoice_line_ids,
            l10n_pe_edi_operation_type=l10n_pe_edi_operation_type,
            invoice_payment_term_id=self.twelve_detraction_balance_cash_id.id,
            payment_method_id=payment_method_id,
            currency_id=self.currency_usd.id,
            aditional_document_reference='F001-456512',
            related_tax_documents_code='99',
            carrier_ref_number='WH/OUT/00004'
        )
        return move_id

    def l10n_pe_edocument_validate_detraction_tags(self, invoice):
        etree = self.l10n_pe_edocument_get_etree_from_move(invoice)
        list_tags = [
            (".//{*}PaymentTerms[1]//{*}ID", 'Detraccion', f"{self.error_label} Etiqueta PaymentTerms/ID erronea"),
            (".//{*}PaymentTerms[1]//{*}PaymentMeansID", '037', f"{self.error_label} Etiqueta PaymentTerms/PaymentMeansID erronea"),
            (".//{*}PaymentTerms[1]//{*}PaymentPercent", '12.0', f"{self.error_label} Etiqueta PaymentTerms/PaymentPercent erronea"),
            (".//{*}PaymentTerms[1]//{*}Amount", '1247.00', f"{self.error_label} Etiqueta PaymentTerms/Amount erronea")
        ]
        self.l10n_pe_edocument_assert_xml_node(etree, list_tags)
