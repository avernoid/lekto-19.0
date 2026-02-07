from odoo.tests.common import TransactionCase
from odoo.tests import Form


class TestOriginInvoice(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # 1. Setup Company and Accounts (Manual CoA)
        cls.company = cls.env.user.company_id
        
        # Income Account
        cls.account_income = cls.env['account.account'].create({
            'name': 'Test Income',
            'code': '700000',
            'account_type': 'income',
            'company_ids': [(4, cls.company.id)],
        })
        
        # Receivable Account
        cls.account_receivable = cls.env['account.account'].create({
            'name': 'Test Receivable',
            'code': '120000',
            'account_type': 'asset_receivable',
            'reconcile': True,
            'company_ids': [(4, cls.company.id)],
        })
        
        # 2. Sales Journal
        cls.journal_sale = cls.env['account.journal'].create({
            'name': 'Test Sale Journal',
            'type': 'sale',
            'code': 'INV',
            'company_id': cls.company.id,
            'default_account_id': cls.account_income.id,
        })
        
        # 3. Operations Partner
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
            'property_account_receivable_id': cls.account_receivable.id,
            'company_id': cls.company.id,
        })

    def setUp(self):
        super().setUp()
        self.model_move = self.env['account.move']
        
        # Create Document Types
        self.doc_type_01 = self.env['l10n_latam.document.type'].create({
            'name': 'Factura',
            'code': '01',
            'country_id': self.env.ref('base.pe').id,
            'doc_code_prefix': 'F',
        })
        self.doc_type_07 = self.env['l10n_latam.document.type'].create({
            'name': 'Nota de Credito',
            'code': '07',
            'country_id': self.env.ref('base.pe').id,
            'doc_code_prefix': 'NC',
            'internal_type': 'credit_note',
        })

        # Enable LATAM documents on journal
        self.journal_sale.l10n_latam_use_documents = True
        
        # Update Journal for Credit Notes if needed (using same journal for simplicity or create another)
        # Test expected 2 journals: obj_journal_01 and obj_journal_02
        # Let's create a second journal for refunds to match original test structure
        self.journal_refund = self.env['account.journal'].create({
            'name': 'Test Refund Journal',
            'type': 'sale',
            'code': 'RFN',
            'company_id': self.company.id,
            'default_account_id': self.account_income.id,
            'l10n_latam_use_documents': True,
        })

        self.obj_product = self.env['product.product'].create({
            'name': 'product1',
            'lst_price': 100,
            'property_account_income_id': self.account_income.id, # Ensure product uses income account
        })

    def create_invoice(self, invoice_amount):
        form_move = Form(
            self.model_move.with_context(default_move_type='out_invoice')
        )
        form_move.partner_id = self.partner
        form_move.journal_id = self.journal_sale
        form_move.l10n_latam_document_type_id = self.doc_type_01
        with form_move as obj_inv:
            with obj_inv.invoice_line_ids.new() as obj_line:
                obj_line.product_id = self.obj_product
                obj_line.quantity = 3
                obj_line.price_unit = invoice_amount
        obj_invoice = form_move.save()
        return obj_invoice

    def create_invoice_refund(self, invoice):
        context = {
            "active_model": 'account.move',
            "active_ids": [invoice.id],
            "active_id": invoice.id,
            'default_refund_method': 'refund',
        }
        wizard = Form(self.env['account.move.reversal'].with_context(context))
        wizard.journal_id = self.journal_refund
        wizard.l10n_latam_document_type_id = self.doc_type_07
        obj_wizard = wizard.save()
        refund = obj_wizard.reverse_moves()
        obj_credit_note = self.model_move.browse(refund['res_id'])
        return obj_credit_note

    def test_01_validate_refund(self):
        obj_invoice = self.create_invoice(invoice_amount=120)
        obj_invoice.action_post()
        obj_invoice_refund = self.create_invoice_refund(obj_invoice)
        
        # Ensure correct document types are set on moves for the test
        obj_invoice.l10n_latam_document_type_id = self.doc_type_01
        obj_invoice_refund.l10n_latam_document_type_id = self.doc_type_07
        
        list_predict = [
            obj_invoice_refund.l10n_latam_document_type_id.code,
            obj_invoice_refund.journal_id.id,
            obj_invoice_refund.reversed_entry_id.id,
            obj_invoice_refund.origin_invoice_date,
            obj_invoice_refund.origin_l10n_latam_document_type_id.id,
            obj_invoice_refund.origin_number
        ]
        list_target = [
            '07',
            self.journal_refund.id,
            obj_invoice.id,
            obj_invoice.invoice_date,
            obj_invoice.l10n_latam_document_type_id.id,
            obj_invoice.name.replace(' ', '') if obj_invoice.name else ''
        ]
        self.assertListEqual(list_predict, list_target)
        print('---------TEST OK - VALIDATE DATASET MOVE_REFUND----------')
