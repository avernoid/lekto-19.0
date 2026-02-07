from pytz import timezone
from datetime import datetime

from odoo.tests.common import tagged
from odoo.tests import common

@tagged('post_install', '-at_install')
class TestPleSaleBook(common.TransactionCase):
    # @classmethod
    def setUp(self):
        super().setUp()

        # Establecer la fecha congelada
        self.frozen_today = datetime(year=2024, month=5, day=30, hour=0, minute=0, second=0, tzinfo=timezone('utc'))

        #Buscar y Actualziar datos de la compañia
        self.company = self.env.ref("base.main_company")
        self.company.write({
            'vat': "20551583041",
            'country_id': self.env.ref('base.pe').id,
            'ple_type_contributor': 'CUO',
        })
        
        # Crear grupo de impuestos
        self.tax_group = self.env['account.tax.group'].create({
            'name': "IGV",
            'l10n_pe_edi_code': "IGV",
        })

        # Crear impuesto
        self.tax_18 = self.env['account.tax'].create({
            'name': 'tax_18',
            'amount_type': 'percent',
            'amount': 18,
            'l10n_pe_edi_tax_code': '1000',
            'l10n_pe_edi_unece_category': 'S',
            'type_tax_use': 'sale',
            'tax_group_id': self.tax_group.id,
        })

        # Crear producto
        self.product = self.env['product.product'].create({
            'name': 'product_ple',

            'uom_id': self.env.ref('uom.product_uom_kgm').id,
            'lst_price': 1000.0,
        })
        
        # Buscar y Actualizar datos del socio
        self.partner_a = self.env['res.partner'].search([('id', '=', 1)], limit=1)
        self.partner_a.write({
            'vat': '20551583041',
            'l10n_latam_identification_type_id': self.env.ref('l10n_pe.it_RUC').id,
            'country_id': self.env.ref('base.pe').id,
        })        
        
        # Obtener el nombre de la hora actual
        self.time_name = datetime.now().strftime('%H%M%S')
        
        #Buscar la moneda de PEN
        self.currency_id = self.env['res.currency'].with_context(active_test=False).search([('name', '=', 'PEN')], limit=1)
        if self.currency_id and not self.currency_id.active:
            self.currency_id.active = True

        # Crear una factura de venta
        move = self.env['account.move'].create({
            'name': 'F FFI-%s1' % self.time_name,
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2024-05-30',
            'date': '2024-05-30',
            'currency_id': self.currency_id.id,
            'invoice_currency_rate': 1.000000,
            'origin_l10n_latam_document_type_id': self.env.ref('l10n_pe.document_type01').id,
            'l10n_latam_document_type_id': self.env.ref('l10n_pe.document_type01').id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                'price_unit': 2000.0,
                'quantity': 5,
                'tax_ids': [(6, 0, self.tax_18.ids)],
            })],
        })
    
        move.action_post()

    def test_ple_sale_book(self):
        # Crear el reporte PLE de ventas
        ple_sale_book = self.env['ple.report.sale'].create({
            'date_start': '2024-05-29',
            'date_end': '2024-05-31',
            'company_id': self.company.id,
            'state_send': '1',
        })
        ple_sale_book.action_generate_excel()
        print("-----------TEST OK-----------")

        # Verificar que se haya generado el archivo Excel y el archivo de texto
        self.assertTrue(ple_sale_book.xls_binary)
        self.assertTrue(ple_sale_book.txt_binary)