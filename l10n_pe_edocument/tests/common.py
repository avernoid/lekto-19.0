from odoo import Command
from odoo.tests import tagged, Form
from odoo.addons.l10n_pe_edi.tests.common import TestPeEdiCommon, mocked_l10n_pe_edi_post_invoice_web_service

from freezegun import freeze_time
import odoo.modules


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPeEdocument(TestPeEdiCommon):

    def setUp(self):
        super(TestL10nPeEdocument, self).setUp()
        self.xml_ubl_pe_model = self.env['account.edi.xml.ubl_pe']
        self.rate_model = self.env['res.currency.rate']
        self.payment_term_model = self.env['account.payment.term']
        self.peru_id = self.env.ref('base.pe')
        self.l10n_pe_partner_company = self.env['res.partner'].create({
            'name': 'Fake Company S.A.C.',
            'vat': '10742124211',
            'l10n_latam_identification_type_id': self.env.ref('l10n_pe.it_RUC').id,
            'country_id': self.peru_id.id,
            'is_company': True
        })
        self.l10n_pe_partner_ruc = self.env['res.partner'].create({
            'name': 'Partner RUC',
            'invoice_sending_method': 'manual',
            'invoice_edi_format': False,
            'property_payment_term_id': self.pay_terms_a.id,
            'property_supplier_payment_term_id': self.pay_terms_a.id,
            'property_account_receivable_id': self.company_data['default_account_receivable'].id,
            'property_account_payable_id': self.company_data['default_account_payable'].id,
            'vat': '15277147740',
            'is_company': True,
            'l10n_latam_identification_type_id': self.env.ref('l10n_pe.it_RUC').id,
            'country_id': self.peru_id.id,
            'parent_id': self.l10n_pe_partner_company.id
        })
        self.three_percent_30days_payment_term_id = self.payment_term_model.create({
            'name': '3% Saldo 30 Days',
            'line_ids': [
                (0, 0, {
                    'value_amount': 97.0,
                    'nb_days': 30,
                    'l10n_pe_is_detraction_retention': False,
                }),
                (0, 0, {
                    'value_amount': 3.0,
                    'nb_days': 1,
                    'l10n_pe_is_detraction_retention': True,
                }),
            ]
        })
        self.thirty_days_payment_term_id = self.payment_term_model.create({
            'name': '30 Days',
            'line_ids': [
                (0, 0, {
                    'value': 'percent',
                    'value_amount': 100.0,
                    'nb_days': 30,
                    'l10n_pe_is_detraction_retention': False
                })
            ]
        })
        self.forty_five_days_payment_term_id = self.payment_term_model.create({
            'name': '45 Days',
            'line_ids': [
                (0, 0, {
                    'value': 'percent',
                    'value_amount': 100.0,
                    'nb_days': 45,
                    'l10n_pe_is_detraction_retention': False
                })
            ]
        })
        self.twelve_detraction_balance_cash_id = self.payment_term_model.create({
            'name': '12% Detracción, Saldo Contado',
            'line_ids': [
                (0, 0, {
                    'value_amount': 12.0,
                    'nb_days': 0,
                    'l10n_pe_is_detraction_retention': True,
                }),
                (0, 0, {
                    'value_amount': 88.0,
                    'nb_days': 0,
                    'l10n_pe_is_detraction_retention': False
                }),
            ]
        })
        self.payment_cash_id = self.payment_term_model.create({
            'name': 'Al contado',
            'line_ids': [
                (0, 0, {
                    'value_amount': 100.0,
                    'nb_days': 0,
                    'l10n_pe_is_detraction_retention': False
                })
            ]
        })

        self.default_transfer_fund_id = self.env['payment.methods.codes'].search([('code', '=', '003')], limit=1)
        self.currency_sol = self.setup_other_currency('PEN', rounding=0.01, rates=[])
        self.currency_usd = self.setup_other_currency('USD', rounding=0.010000, rates=[('2017-01-01', 0.271591526344),('2017-01-02', 0.270782561603)])
        self.company_data['company'].write({'currency_id': self.currency_sol.id})

        self.product_detraction = self.env['product.product'].create({
            'name': 'Test Product detraction - l10n_pe_edocument',
            'list_price': 100.0,
            'standard_price': 80.0,
            'weight': 2,
            # 'uom_po_id': self.env.ref('uom.product_uom_kgm').id,
            'uom_id': self.env.ref('uom.product_uom_kgm').id,
            'property_account_income_id': self.company_data['default_account_revenue'].id,
            'property_account_expense_id': self.company_data['default_account_expense'].id,
            'unspsc_code_id': self.env.ref('product_unspsc.unspsc_code_01010101').id,
            'l10n_pe_withhold_code': '037',  # codigo de detracción
            'l10n_pe_withhold_percentage': 12,  # porcentaje de detracción'
        })
        self.product_test_2 = self.env['product.product'].create({
            'name': 'Test Product 2 - l10n_pe_edocument',
            'list_price': 100.0,
            'standard_price': 80.0,
            'weight': 2,
            # 'uom_po_id': self.env.ref('uom.product_uom_kgm').id,
            'uom_id': self.env.ref('uom.product_uom_kgm').id,
            'property_account_income_id': self.company_data['default_account_revenue'].id,
            'property_account_expense_id': self.company_data['default_account_expense'].id,
            'unspsc_code_id': self.env.ref('product_unspsc.unspsc_code_01010101').id
        })
        self.l10n_pe_gra_tax_group = self.env['account.tax.group'].create({
            'name': "GRA",
            'l10n_pe_edi_code': "GRA",
            'country_id': self.peru_id.id
        })
        self.l10n_pe_icbper_tax_group = self.env['account.tax.group'].create({
            'name': "ICBPER",
            'l10n_pe_edi_code': "ICBPER",
            'country_id': self.peru_id.id
        })
        self.l10n_pe_free_invoice_tax_group = self.env['account.tax.group'].create({
            'name': "FREE INVOICE",
            'country_id': self.peru_id.id
        })
        self.tax_withdrawal_due_to_bonus = self.env['account.tax'].create({
            'name': '0% Obsequio - Retiro por bonificación - TEST',
            'amount_type': 'percent',
            'amount': 0.0,
            'l10n_pe_edi_tax_code': '9996',
            'l10n_pe_edi_unece_category': 'Z',
            'l10n_pe_edi_affectation_reason': '31',
            'type_tax_use': 'sale',
            'tax_group_id': self.l10n_pe_gra_tax_group.id,
        })
        self.tax_18_withdrawal_due_to_prize = self.env['account.tax'].create({
            'name': '18% Retiro - Retiro por premio - TEST',
            'amount_type': 'percent',
            'amount': 18.0,
            'l10n_pe_edi_tax_code': '9996',
            'l10n_pe_edi_unece_category': 'Z',
            'l10n_pe_edi_affectation_reason': '11',
            'type_tax_use': 'sale',
            'tax_group_id': self.l10n_pe_gra_tax_group.id,
        })
        self.tax_icbper = self.env['account.tax'].create({
            'name': 'ICBPER - TEST',
            'amount_type': 'fixed',
            'amount': 0.5,
            'l10n_pe_edi_tax_code': '7152',
            'l10n_pe_edi_unece_category': False,
            'l10n_pe_edi_affectation_reason': False,
            'type_tax_use': 'sale',
            'tax_group_id': self.l10n_pe_icbper_tax_group.id,
        })
        self.tax_free_group_account_id_1 = self.env['account.account'].create({
            'code': '4011100X',
            'name': 'Gobierno nacional - Impuesto general a las ventas - IGV – Cuenta propia - Test',
            'account_type': 'liability_current',
            'reconcile': False
        })
        self.tax_free_group_account_id_2 = self.env['account.account'].create({
            'code': '6411000X',
            'name': 'Gobierno nacional - Impuesto general a las ventas y selectivo al consumo',
            'account_type': 'expense',
            'reconcile': False
        })
        self.tax_free_group_sub_tax_1 = self.env['account.tax'].create({
            'name': 'Substraer base - TEST',
            'amount_type': 'percent',
            'amount': -100.0,
            'l10n_pe_edi_tax_code': False,
            'l10n_pe_edi_unece_category': False,
            'l10n_pe_edi_affectation_reason': False,
            'type_tax_use': 'none',
            'invoice_label': '-Base',
            'description': 'SUB BASE',
            'tax_group_id': self.l10n_pe_free_invoice_tax_group.id,
            'is_base_affected': True,
            'include_base_amount': False
        })
        self.tax_free_group_sub_tax_2 = self.env['account.tax'].create({
            'name': '18% Libre de Impuestos - TEST',
            'amount_type': 'percent',
            'amount': 18.0,
            'l10n_pe_edi_tax_code': '9996',
            'l10n_pe_edi_unece_category': 'E',
            'l10n_pe_edi_affectation_reason': '11',
            'type_tax_use': 'none',
            'invoice_label': '18% Free',
            'description': '18% Libre',
            'tax_group_id': self.l10n_pe_gra_tax_group.id,
            'is_base_affected': True,
            'include_base_amount': False
        })
        self.tax_free_group_sub_tax_3 = self.env['account.tax'].create({
            'name': '-18% Libre de Impuestos Gasto - TEST',
            'amount_type': 'percent',
            'amount': -18.0,
            'l10n_pe_edi_tax_code': False,
            'l10n_pe_edi_unece_category': False,
            'l10n_pe_edi_affectation_reason': False,
            'type_tax_use': 'none',
            'invoice_label': '-18% Free',
            'description': '-18% Libre',
            'tax_group_id': self.l10n_pe_free_invoice_tax_group.id,
            'is_base_affected': True,
            'include_base_amount': False
        })
        self.l10n_pe_edocument_set_account_id_in_taxes(self.tax_free_group_sub_tax_2, self.tax_free_group_account_id_1)
        self.l10n_pe_edocument_set_account_id_in_taxes(self.tax_free_group_sub_tax_3, self.tax_free_group_account_id_2)
        self.tax_free_group = self.env['account.tax'].create({
            'name': '18% Libre final - TEST',
            'amount_type': 'group',
            'l10n_pe_edi_tax_code': '9996',
            'l10n_pe_edi_unece_category': False,
            'l10n_pe_edi_affectation_reason': '11',
            'type_tax_use': 'sale',
            'children_tax_ids': [(6, 0, [self.tax_free_group_sub_tax_1.id, self.tax_free_group_sub_tax_2.id, self.tax_free_group_sub_tax_3.id])],
            'country_id': self.peru_id.id,
            'description': '18% Libre Grupo - TEST',
        })

        self.tax_free_zero_percent_sub_tax_2 = self.env['account.tax'].create({
            'name': '0% Gra - TEST',
            'amount_type': 'percent',
            'amount': 0.0,
            'l10n_pe_edi_tax_code': '9996',
            'l10n_pe_edi_unece_category': 'Z',
            'l10n_pe_edi_affectation_reason': '21',
            'type_tax_use': 'sale',
            'invoice_label': 'GRA',
            'description': '0% Gratis',
            'tax_group_id': self.l10n_pe_gra_tax_group.id,
            'is_base_affected': True,
            'include_base_amount': False
        })
        self.tax_free_zero_percent = self.env['account.tax'].create({
            'name': 'GRATUITO 0% - TEST',
            'amount_type': 'group',
            'l10n_pe_edi_tax_code': '9996',
            'l10n_pe_edi_unece_category': 'Z',
            'l10n_pe_edi_affectation_reason': '21',
            'type_tax_use': 'sale',
            'children_tax_ids': [(6, 0, [self.tax_free_group_sub_tax_1.id, self.tax_free_zero_percent_sub_tax_2.id])],
            'country_id': self.peru_id.id,
            'description': '18% Libre Grupo - TEST',
        })

    def l10n_pe_edocument_set_account_id_in_taxes(self, tax, account_id):
        tax.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').write({'account_id': account_id})
        tax.refund_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').write({'account_id': account_id})

    def l10n_pe_edocument_get_etree_from_move(self, invoice):
        generated_files = self._process_documents_web_services(invoice, {'pe_ubl_2_1'})
        self.assertTrue(generated_files)
        zip_edi_str = generated_files[0]
        edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)
        current_etree = self.get_xml_tree_from_string(edi_xml)
        print(edi_xml)
        return current_etree

    def l10n_pe_edocument_compare_expected_xmls(self, invoice, expected_xml_str):
        current_etree = self.l10n_pe_edocument_get_etree_from_move(invoice)
        expected_etree = self.get_xml_tree_from_string(expected_xml_str)
        self.assertXmlTreeEqual(current_etree, expected_etree)

    def l10n_pe_edocument_assert_xml_node(self, node, list_tags):
        for xpath, expected_value, message in list_tags:
            elements = node.findall(xpath)
            self.assertTrue(elements, f"{message}: Nodes {xpath} not found.")
            for element in elements:
                self.assertEqual(element.text, expected_value, f"{message}: Value of {xpath} is not as expected.")

    @staticmethod
    def l10n_pe_edocument_load_tpl(tpl_file):
        with open(odoo.tools.misc.file_path(f'l10n_pe_edocument/tests/data/{tpl_file}'), 'r', encoding='utf-8') as f:
            load_tpl = f.read()
            return load_tpl