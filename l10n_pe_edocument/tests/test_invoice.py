from odoo.tests import tagged
from odoo.addons.l10n_pe_edi.tests.common import mocked_l10n_pe_edi_post_invoice_web_service
from .common import TestL10nPeEdocument
from unittest.mock import patch
from freezegun import freeze_time
import odoo.modules


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPeInvoice(TestL10nPeEdocument):

    def setUp(self):
        super(TestL10nPeInvoice, self).setUp()
        self.error_label = "l10n_pe_edocument - Invoice:"
        self.expected_invoice_sol_withdrawal_due_to_bonus_tpl = self.l10n_pe_edocument_load_tpl("invoice_sol_withdrawal_due_to_bonus.xml")
        self.expected_invoice_sol_tax_igv_with_zero_line_tpl = self.l10n_pe_edocument_load_tpl('invoice_sol_tax_igv_with_zero_line.xml')
        self.expected_invoice_sol_tax_icbper_tpl = self.l10n_pe_edocument_load_tpl('invoice_sol_tax_icbper.xml')
        self.expected_invoice_sol_tax_free_group_tpl = self.l10n_pe_edocument_load_tpl('invoice_sol_tax_free_group.xml')
        self.expected_invoice_sol_tax_igv_and_free_group_tpl = self.l10n_pe_edocument_load_tpl('invoice_sol_tax_igv_and_free_group.xml')
        self.expected_invoice_sol_tax_free_zero_percent_tpl = self.l10n_pe_edocument_load_tpl('invoice_sol_tax_free_zero_percent.xml')
        self.expected_invoice_sol_tax_igv_and_free_zero_percent_tpl = self.l10n_pe_edocument_load_tpl('invoice_sol_tax_igv_and_free_zero_percent.xml')
        self.expected_invoice_sol_tax_igv_and_free_zero_percent_and_free_group_tpl = self.l10n_pe_edocument_load_tpl(
            'invoice_sol_tax_igv_and_free_zero_percent_and_free_group.xml')
        self.expected_invoice_sol_tax_igv_icbper_and_free_group_tpl = self.l10n_pe_edocument_load_tpl('invoice_sol_tax_igv_icbper_and_free_group.xml')
        self.expected_invoice_sol_tax_igv_and_free_group_icbper_tpl = self.l10n_pe_edocument_load_tpl('invoice_sol_tax_igv_and_free_group_icbper.xml')

    def test_invoice_sol_tax_withdrawal_due_to_bonus(self):
        """
            Funcionalidad:
            - <f2> Referencia de cliente
            - <f3> Retiro por bonificación
        """
        with (freeze_time(self.frozen_today), \
              patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                    new=mocked_l10n_pe_edi_post_invoice_web_service)):
            invoice_line_ids = [(0, 0, {
                'product_id': self.product.id,
                'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                'price_unit': 240.0,
                'quantity': 1,
                'tax_ids': [(6, 0, self.tax_18.ids)],
            }), (0, 0, {
                'product_id': self.product_test_2.id,
                'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                'price_unit': 2.0,
                'quantity': 1,
                'tax_ids': [(6, 0, self.tax_withdrawal_due_to_bonus.ids)],
            })]
            move_id = self._create_invoice(
                currency_id=self.currency_sol.id,
                invoice_line_ids=invoice_line_ids,
                ref='Retiro por bonificación - Prueba de longitud de campo en referencia de la orden'
            )
            move_id.action_post()
            expected_invoice_sol_withdrawal_due_to_bonus_xml = self.expected_invoice_sol_withdrawal_due_to_bonus_tpl.format(
                order_reference='Retiroporbonificacio'
            )
            self.l10n_pe_edocument_compare_expected_xmls(move_id, expected_invoice_sol_withdrawal_due_to_bonus_xml)

    def test_invoice_sol_tax_igv_despatch_document_reference(self):
        """
            Funcionalidad:
            - <f7> Guía de Remisión
        """
        with (freeze_time(self.frozen_today), \
              patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                    new=mocked_l10n_pe_edi_post_invoice_web_service)):
            move_id = self._create_invoice(
                currency_id=self.currency_sol.id,
                carrier_ref_number='WH/OUT/00004'
            )
            move_id.action_post()
            self.validate_despatch_document_reference_tag(move_id)
    #
    def test_invoice_sol_tax_igv_with_zero_line(self):
        """
            Funcionalidad:
            - <f11> Zero line
        """
        with (freeze_time(self.frozen_today), \
              patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                    new=mocked_l10n_pe_edi_post_invoice_web_service)):
            invoice_line_ids = [(0, 0, {
                'product_id': self.product.id,
                'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                'price_unit': 150.0,
                'quantity': 1,
                'tax_ids': [(6, 0, self.tax_18.ids)],
            }), (0, 0, {
                'product_id': self.product_test_2.id,
                'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                'price_unit': 0.0,
                'quantity': 1,
                'tax_ids': [(6, 0, self.tax_18.ids)],
            })]
            move_id = self._create_invoice(
                currency_id=self.currency_sol.id,
                invoice_line_ids=invoice_line_ids
            )
            move_id.action_post()
            self.l10n_pe_edocument_compare_expected_xmls(move_id, self.expected_invoice_sol_tax_igv_with_zero_line_tpl)

    # def test_invoice_sol_tax_icbper(self):
    #     """
    #         Funcionalidad:
    #         - <f12>ICBPER
    #     """
    #     with (freeze_time(self.frozen_today), \
    #           patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
    #                 new=mocked_l10n_pe_edi_post_invoice_web_service)):
    #         invoice_line_ids = [(0, 0, {
    #             'product_id': self.product.id,
    #             'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
    #             'price_unit': 150.0,
    #             'quantity': 1,
    #             'tax_ids': [(6, 0, [self.tax_18.id, self.tax_icbper.id])]
    #         })]
    #         move_id = self._create_invoice(
    #             currency_id=self.currency_sol.id,
    #             invoice_line_ids=invoice_line_ids
    #         )
    #         move_id.action_post()
    #         self.l10n_pe_edocument_compare_expected_xmls(move_id, self.expected_invoice_sol_tax_icbper_tpl)


    # def test_invoice_sol_tax_igv_and_free_group(self):
    #     """
    #         Funcionalidad:
    #         - <f10> Múltiples impuestos
    #         - Ejemplo 1: IGV/ 18% Libre (Nativo)
    #     """
    #     with (freeze_time(self.frozen_today), \
    #           patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
    #                 new=mocked_l10n_pe_edi_post_invoice_web_service)):
    #         invoice_line_ids = [(0, 0, {
    #             'product_id': self.product.id,
    #             'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
    #             'price_unit': 10.0,
    #             'quantity': 1,
    #             'tax_ids': [(6, 0, self.tax_18.ids)],
    #         }), (0, 0, {
    #             'product_id': self.product_test_2.id,
    #             'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
    #             'price_unit': 10.0,
    #             'quantity': 1,
    #             'tax_ids': [(6, 0, self.tax_free_group.ids)],
    #         })]
    #         move_id = self._create_invoice(
    #             currency_id=self.currency_sol.id,
    #             invoice_line_ids=invoice_line_ids,
    #             l10n_pe_edi_legend='1002'
    #         )
    #         move_id.action_post()
    #         self.l10n_pe_edocument_compare_expected_xmls(move_id, self.expected_invoice_sol_tax_igv_and_free_group_tpl)

    # def test_invoice_sol_tax_igv_icbper_and_free_group(self):
    #     """
    #         Funcionalidad:
    #         - <f10> Múltiples impuestos
    #         - Ejemplo 2: IGV / ICBPER + 18% Libre (Nativo)
    #     """
    #     with (freeze_time(self.frozen_today), \
    #           patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
    #                 new=mocked_l10n_pe_edi_post_invoice_web_service)):
    #         invoice_line_ids = [(0, 0, {
    #             'product_id': self.product.id,
    #             'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
    #             'price_unit': 15.25,
    #             'quantity': 100,
    #             'tax_ids': [(6, 0, [self.tax_18.id, self.tax_icbper.id])]
    #         }), (0, 0, {
    #             'product_id': self.product_test_2.id,
    #             'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
    #             'price_unit': 10.0,
    #             'quantity': 1,
    #             'tax_ids': [(6, 0, self.tax_free_group.ids)],
    #         })]
    #         move_id = self._create_invoice(
    #             currency_id=self.currency_sol.id,
    #             invoice_line_ids=invoice_line_ids,
    #             l10n_pe_edi_legend='1002'
    #         )
    #         move_id.action_post()
    #         self.l10n_pe_edocument_compare_expected_xmls(move_id, self.expected_invoice_sol_tax_igv_icbper_and_free_group_tpl)

    # def test_invoice_sol_tax_igv_and_free_group_icbper(self):
    #     """
    #         Funcionalidad:
    #         - <f10> Múltiples impuestos
    #         - Ejemplo 3: IGV + 18% Libre (Nativo) - ICBPER
    #     """
    #     with (freeze_time(self.frozen_today), \
    #           patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
    #                 new=mocked_l10n_pe_edi_post_invoice_web_service)):
    #         invoice_line_ids = [(0, 0, {
    #             'product_id': self.product.id,
    #             'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
    #             'price_unit': 20.0,
    #             'quantity': 1,
    #             'tax_ids': [(6, 0, self.tax_18.ids)]
    #         }), (0, 0, {
    #             'product_id': self.product_test_2.id,
    #             'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
    #             'price_unit': 10.0,
    #             'quantity': 1,
    #             'tax_ids': [(6, 0, [self.tax_free_group.id, self.tax_icbper.id])],
    #         })]
    #         move_id = self._create_invoice(
    #             currency_id=self.currency_sol.id,
    #             invoice_line_ids=invoice_line_ids,
    #             l10n_pe_edi_legend='1002'
    #         )
    #         move_id.action_post()
    #         self.l10n_pe_edocument_compare_expected_xmls(move_id, self.expected_invoice_sol_tax_igv_and_free_group_icbper_tpl)
    #
    # def test_invoice_sol_tax_igv_and_free_zero_percent(self):
    #     """
    #         Funcionalidad:
    #         - <f16> Múltiples TAXES by line
    #         - Ejemplo 4: IGV 18% + GRATUITO 0%
    #     """
    #     with (freeze_time(self.frozen_today), \
    #           patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
    #                 new=mocked_l10n_pe_edi_post_invoice_web_service)):
    #         invoice_line_ids = [(0, 0, {
    #             'product_id': self.product.id,
    #             'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
    #             'price_unit': 337.0,
    #             'quantity': 1,
    #             'tax_ids': [(6, 0, self.tax_18.ids)]
    #         }), (0, 0, {
    #             'product_id': self.product_test_2.id,
    #             'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
    #             'price_unit': 10.0,
    #             'quantity': 1,
    #             'tax_ids': [(6, 0, self.tax_free_zero_percent.ids)],
    #         })]
    #         move_id = self._create_invoice(
    #             currency_id=self.currency_sol.id,
    #             invoice_line_ids=invoice_line_ids,
    #             l10n_pe_edi_legend='1002'
    #         )
    #         move_id.action_post()
    #         expected_invoice_sol_tax_igv_and_free_zero_percent_xml = self.expected_invoice_sol_tax_igv_and_free_zero_percent_tpl.format(
    #             order_reference=self.xml_ubl_pe_model._l10n_pe_edi_get_order_reference(move_id)
    #         )
    #         self.l10n_pe_edocument_compare_expected_xmls(move_id, expected_invoice_sol_tax_igv_and_free_zero_percent_xml)
    #
    # def test_invoice_sol_tax_igv_and_free_zero_percent_and_free_group(self):
    #     """
    #         Funcionalidad:
    #         - <f16> Múltiples TAXES by line
    #         - Ejemplo 5: IGV 18% + GRATUITO 0% + Libre 18%
    #     """
    #     with (freeze_time(self.frozen_today), \
    #           patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
    #                 new=mocked_l10n_pe_edi_post_invoice_web_service)):
    #         invoice_line_ids = [(0, 0, {
    #             'product_id': self.product.id,
    #             'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
    #             'price_unit': 10.0,
    #             'quantity': 1,
    #             'tax_ids': [(6, 0, self.tax_18.ids)]
    #         }), (0, 0, {
    #             'product_id': self.product_test_2.id,
    #             'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
    #             'price_unit': 10.0,
    #             'quantity': 1,
    #             'tax_ids': [(6, 0, self.tax_free_zero_percent.ids)],
    #         }), (0, 0, {
    #             'product_id': self.product_test_2.id,
    #             'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
    #             'price_unit': 10.0,
    #             'quantity': 1,
    #             'tax_ids': [(6, 0, self.tax_free_group.ids)],
    #         })]
    #         move_id = self._create_invoice(
    #             currency_id=self.currency_sol.id,
    #             invoice_line_ids=invoice_line_ids,
    #             l10n_pe_edi_legend='1002'
    #         )
    #         move_id.action_post()
    #         expected_invoice_sol_tax_igv_and_free_zero_percent_and_free_group_xml = self.expected_invoice_sol_tax_igv_and_free_zero_percent_and_free_group_tpl.format(
    #             order_reference=self.xml_ubl_pe_model._l10n_pe_edi_get_order_reference(move_id)
    #         )
    #         self.l10n_pe_edocument_compare_expected_xmls(move_id, expected_invoice_sol_tax_igv_and_free_zero_percent_and_free_group_xml)

    # def test_invoice_sol_tax_free_group(self):
    #     """
    #         Funcionalidad:
    #         - Test 1 <f15> 18% Libre Final (Nativo)
    #     """
    #     with (freeze_time(self.frozen_today), \
    #           patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
    #                 new=mocked_l10n_pe_edi_post_invoice_web_service)):
    #         invoice_line_ids = [(0, 0, {
    #             'product_id': self.product.id,
    #             'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
    #             'price_unit': 100.0,
    #             'quantity': 1,
    #             'tax_ids': [(6, 0, self.tax_free_group.ids)],
    #         })]
    #         move_id = self._create_invoice(
    #             currency_id=self.currency_sol.id,
    #             invoice_line_ids=invoice_line_ids,
    #             l10n_pe_edi_legend='1002'
    #         )
    #         move_id.action_post()
    #         expected_invoice_sol_tax_free_group_xml = self.expected_invoice_sol_tax_free_group_tpl
    #         self.l10n_pe_edocument_compare_expected_xmls(move_id, expected_invoice_sol_tax_free_group_xml)

    # def test_invoice_sol_tax_free_zero_percent(self):
    #     """
    #         Funcionalidad:
    #         - Test 2 <f14> GRATUITO 0%
    #     """
    #     with (freeze_time(self.frozen_today), \
    #           patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
    #                 new=mocked_l10n_pe_edi_post_invoice_web_service)):
    #         invoice_line_ids = [(0, 0, {
    #             'product_id': self.product.id,
    #             'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
    #             'price_unit': 337.0,
    #             'quantity': 1,
    #             'tax_ids': [(6, 0, self.tax_free_zero_percent.ids)],
    #         })]
    #         move_id = self._create_invoice(
    #             currency_id=self.currency_sol.id,
    #             invoice_line_ids=invoice_line_ids,
    #             l10n_pe_edi_legend='1002'
    #         )
    #         move_id.action_post()
    #         expected_invoice_sol_tax_free_zero_percent_xml = self.expected_invoice_sol_tax_free_zero_percent_tpl
    #         self.l10n_pe_edocument_compare_expected_xmls(move_id, expected_invoice_sol_tax_free_zero_percent_xml)

    def validate_despatch_document_reference_tag(self, move_id):
        list_tags = [
            (".//{*}DespatchDocumentReference//{*}ID", move_id.carrier_ref_number, f"{self.error_label} Etiqueta DespatchDocumentReference/ID erronea"),
            (".//{*}DespatchDocumentReference//{*}DocumentTypeCode", '09', f"{self.error_label} DespatchDocumentReference/DocumentTypeCode erronea")
        ]
        etree = self.l10n_pe_edocument_get_etree_from_move(move_id)
        self.l10n_pe_edocument_assert_xml_node(etree, list_tags)
