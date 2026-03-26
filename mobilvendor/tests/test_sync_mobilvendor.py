# -*- coding: utf-8 -*-
from datetime import date
import unittest
from unittest.mock import patch, MagicMock

from odoo.tests.common import TransactionCase
from odoo.addons.mobilvendor.services.mobilvendor_api import MobilvendorAPIHandler

class TestSyncMobilvendor(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create standard accounting setup for Odoo 19
        cls.income_account = cls.env['account.account'].create({
            'name': 'Test Income',
            'code': '200000',
            'account_type': 'income',
            'company_ids': [(4, cls.env.user.company_id.id)],
        })
        cls.sale_journal = cls.env['account.journal'].create({
            'name': 'Test Sales Journal',
            'code': 'TSJ',
            'type': 'sale',
            'default_account_id': cls.income_account.id,
            'company_id': cls.env.user.company_id.id,
        })
        cls.receivable_account = cls.env['account.account'].create({
            'name': 'Test Receivable',
            'code': '121200',
            'account_type': 'asset_receivable',
            'company_ids': [(4, cls.env.user.company_id.id)],
        })
        
        # Create required partner, product, and stock location
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Customer',
            'mobilvendor_id': 'CUST1',
            'vat': '1234567890',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'type': 'consu',
            'is_storable': True,
            'list_price': 100.0,
            'property_account_income_id': cls.income_account.id,
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Vendor',
            'mobilvendor_code': 'USR1'
        })
        
        cls.route = cls.env['mobilvendor.route'].create({
            'name': 'Test Route',
            'mobilvendor_id': 'ROUTE1',
            'invoice_journal_id': cls.sale_journal.id
        })
        
        # Configure company for sync
        cls.env.company.write({
            'mobilvendor_api_username': 'test',
            'mobilvendor_api_password': 'test',
            'mobilvendor_api_url': 'http://test.com',
            'mobilvendor_api_context': 'test',
        })

    @patch('odoo.addons.mobilvendor.services.mobilvendor_api.MobilvendorAPIHandler._send_get_request')
    def test_01_sync_new_canceled_invoice(self, mock_get_request):
        """Test syncing a NEW invoice that is ALREADY canceled (status=3) in Mobilvendor"""
        # Mock API Response
        mock_get_request.return_value = {
            "pages": 1,
            "headers": [{
                "code": "INV-CANC-001",
                "type": "1",
                "status": "3",  # Canceled
                "customer_code": "CUST1",
                "create_date": int(date.today().strftime('%s')) if hasattr(date, 'strftime') else 1678888888,
                "description": "Test Canceled Inv",
                "discount": 0.0,
                "subtotal": 100.0,
                "subtotal_amount": 100.0,
                "iva_base": 0.0,
                "iva_0_base": 100.0,
                "iva_amount": 0.0,
                "total": 100.0,
                "secuence": "001-001-000000001",
                "user": {"code": "USR1"},
                "user_route": {"code": "ROUTE1"}
            }],
            "details": [{
                "invoice_code": "INV-CANC-001",
                "article_code": str(self.product.product_tmpl_id.id),
                "quantity": 1,
                "price": 100.0,
                "subtotal": 100.0,
                "discount": 0.0,
                "description": "Test Product"
            }]
        }
        
        # Execute Sync
        handler = MobilvendorAPIHandler(self.env.company, self.env)
        handler._process_invoices_page(1, '1', '2026-03-01')
        
        # Verify
        invoice = self.env['account.move'].search([('mobilvendor_id', '=', 'INV-CANC-001')])
        self.assertTrue(invoice, "Invoice should be created")
        self.assertEqual(invoice.state, 'cancel', "New canceled invoice should be created directly in 'cancel' state")
        
        pickings = self.env['stock.picking'].search([('origin', '=', 'INV-CANC-001')])
        self.assertFalse(pickings, "No inventory movement should be generated for a new canceled invoice")

    @patch('odoo.addons.mobilvendor.services.mobilvendor_api.MobilvendorAPIHandler._send_get_request')
    def test_02_sync_existing_invoice_cancellation(self, mock_get_request):
        """Test syncing an EXISTING valid invoice that becomes canceled (status=3) in Mobilvendor"""
        
        # 1. Create the existing valid invoice manually (to simulate it was already synced)
        valid_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'invoice_date': date.today(),
            'journal_id': self.sale_journal.id,
            'mobilvendor_id': 'INV-VALID-002',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 100.0,
                'account_id': self.income_account.id,
            })],
        })
        valid_invoice._post(soft=False)
        
        # Generar picking perfecto de salida usando el API Handler
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        api_handler = MobilvendorAPIHandler(self.env.company, self.env)
        
        # Inject stock to prevent backorders
        self.env['stock.quant']._update_available_quantity(self.product, warehouse.lot_stock_id, 10.0)
        
        details = [{
            "article_code": str(self.product.product_tmpl_id.id),
            "quantity": 1.0,
            "org_storage_code": str(warehouse.lot_stock_id.id),
            "dest_storage_code": str(self.env.ref('stock.stock_location_customers').id),
            "invoice_code": "INV-VALID-002",
        }]
        api_handler._mobilvendor_update_inventory_storages(
            line_items=details,
            partner_id=self.partner.id,
            transfer_type='INVOICE'
        )
        
        picking = self.env['stock.picking'].search([('origin', '=', 'Invoice INV-VALID-002')], limit=1)
        
        # Ensure it's done
        if picking:
            self.assertEqual(picking.state, 'done', "Picking should be done")
        self.assertEqual(valid_invoice.state, 'posted', "Invoice should be posted")
        
        # 2. Mock API Response returning the SAME invoice but now status=3
        mock_get_request.return_value = {
            "pages": 1,
            "headers": [{
                "code": "INV-VALID-002",
                "type": "1",
                "status": "3",  # Now Canceled
                "customer_code": "CUST1",
                "create_date": int(date.today().strftime('%s')) if hasattr(date, 'strftime') else 1678888888,
                "description": "Test Inv",
                "discount": 0.0,
                "subtotal": 100.0,
                "subtotal_amount": 100.0,
                "iva_base": 0.0,
                "iva_0_base": 100.0,
                "iva_amount": 0.0,
                "total": 100.0,
                "secuence": "001-001-000000002",
                "user": {"code": "USR1"},
                "user_route": {"code": "ROUTE1"}
            }],
            "details": [{
                "invoice_code": "INV-VALID-002",
                "article_code": str(self.product.product_tmpl_id.id),
                "quantity": 1,
                "price": 100.0,
                "subtotal": 100.0,
                "discount": 0.0,
                "description": "Test Product"
            }]
        }
        
        # 3. Execute Sync
        handler = MobilvendorAPIHandler(self.env.company, self.env)
        handler._process_invoices_page(1, '1', '2026-03-01')
        
        # 4. Verify Reversal
        valid_invoice.invalidate_recordset()
        self.assertEqual(valid_invoice.state, 'cancel', "The existing invoice should now be canceled")
        
        # Verify a return picking was generated
        return_picking = self.env['stock.picking'].search([
            ('picking_type_id.code', '=', 'incoming'),
            ('partner_id', '=', self.partner.id),
            ('state', 'in', ['done', 'assigned', 'confirmed'])
        ])
        self.assertTrue(return_picking, "A validated return picking should have been created")
        self.assertEqual(len(return_picking), 1, "Exactly one return picking should exist")

    @patch('odoo.addons.mobilvendor.services.mobilvendor_api.MobilvendorAPIHandler._send_get_request')
    def test_03_sync_canceled_payments(self, mock_get_request):
        """Test syncing payments that are annulled (status=0)"""
        # Create a journal for payments
        cp_journal = self.env['account.journal'].create({
            'name': 'Bank Journal',
            'type': 'bank',
            'code': 'BNK',
            'company_id': self.env.user.company_id.id,
        })
        self.env.company.mobilvendor_payment_journal_id = cp_journal.id
        
        # 1. Create existing invoice (to be paid and canceled)
        valid_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'invoice_date': date.today(),
            'journal_id': self.sale_journal.id,
            'mobilvendor_id': 'INV-VALID-002',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 100.0,
                'account_id': self.income_account.id,
            })],
        })
        valid_invoice._post(soft=False)

        # Mock payment request (status=0 means canceled payment)
        mock_get_request.return_value = {
            "pages": 1,
            "headers": [{
                "code": "PAY-CANC-001",
                "date": date.today().strftime('%Y-%m-%d'),
                "total": 100.0,
                "customer": {"code": "CUST1"},
                "user": {"code": "USR1"},
            }],
            "details": [],
            "records": [{
                "code": "PAY-CANC-001",
                "type": "1",
                "status": "0" # CANCELED
            }],
            "payments": [{
                "payment_code": "PAY-CANC-001",
                "payment": 100.0,
                "invoice_code": "INV-VALID-002",
                "payment_method": {"code": "1"}
            }]
        }
        
        # Execute Sync
        handler = MobilvendorAPIHandler(self.env.company, self.env)
        handler._process_payments_page(1, date.today(), '2026-03-01')
        
        # Verify the payment is created but canceled
        payment = self.env['account.payment'].search([('mobilvendor_id', '=', 'PAY-CANC-001')])
        self.assertTrue(payment, "Canceled payment should be created in Odoo")
        self.assertEqual(payment.state, 'canceled', "Canceled payment should have 'canceled' state")
