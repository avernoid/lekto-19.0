from odoo.tests.common import TransactionCase
from datetime import date, timedelta

class TestFinancialAnnexes(TransactionCase):

    def setUp(self):
        super(TestFinancialAnnexes, self).setUp()
        
        # Setup Dates
        self.today = date.today()
        
        # Setup Company and Partner
        self.company = self.env.company
        self.partner = self.env['res.partner'].create({'name': 'Test Supplier', 'supplier_rank': 1})
        
        # Setup Accounts
        self.account_payable = self.env['account.account'].create({
            'code': '421200TEST',
            'name': 'Test Payable',
            'account_type': 'liability_payable',
            'reconcile': True,
        })
        self.account_expense = self.env['account.account'].create({
            'code': '600000TEST',
            'name': 'Test Expense',
            'account_type': 'expense',
        })
        
        # Outstanding Account (Bridge Account for Payments)
        self.account_outstanding = self.env['account.account'].create({
            'code': '101000OUT',
            'name': 'Outstanding Payments',
            'account_type': 'asset_current',
            'reconcile': True,
        })

        # Set Partner Payable Account
        self.partner.property_account_payable_id = self.account_payable
        
        # Setup Journals
        self.journal_purchase = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
        if not self.journal_purchase:
            self.journal_purchase = self.env['account.journal'].create({
                'name': 'Test Purchase Journal',
                'code': 'TPUR',
                'type': 'purchase',
            })

        self.journal_bank = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
        if not self.journal_bank:
            self.journal_bank = self.env['account.journal'].create({
                'name': 'Test Bank Journal',
                'code': 'TBNK',
                'type': 'bank',
            })
            
        # Ensure Bank Journal has Outstanding Account configured for Outbound Payments
        # In Odoo 19, this is often on the journal 'outbound_payment_method_line_ids' or journal default
        # We will set it on the journal's default outbound account property if available, or modifying the payment method line.
        
        # Easiest way in modern Odoo: Set 'suspense_account_id' (not directly outstanding) but usually 'outbound_payment_method_line_ids'
        # Let's ensure the manual payment method exists
        manual_method = self.env.ref('account.account_payment_method_manual_out')
        
        # Find or Create the payment method line for this journal
        pml = self.journal_bank.outbound_payment_method_line_ids.filtered(lambda l: l.payment_method_id == manual_method)
        if not pml:
            self.journal_bank.write({
                'outbound_payment_method_line_ids': [(0, 0, {
                    'payment_method_id': manual_method.id,
                    'payment_account_id': self.account_outstanding.id, # Explicitly set account here
                })]
            })
        else:
            # If exists, ensure it has an account or the journal has one.
            # We force update the first one to ensure test reliability
            pml[0].write({'payment_account_id': self.account_outstanding.id})


        # Document Type (L10n Latam) - Optional, handle if exists
        self.document_type = False
        if 'l10n_latam.document.type' in self.env:
            self.document_type = self.env['l10n_latam.document.type'].search([('code', '=', '01')], limit=1)

    def create_invoice(self, date_invoice, amount):
        vals = {
            'move_type': 'in_invoice',
            'partner_id': self.partner.id,
            'invoice_date': date_invoice,
            'date': date_invoice,
            'journal_id': self.journal_purchase.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Test Expense',
                'quantity': 1,
                'price_unit': amount,
                'account_id': self.account_expense.id,
            })],
        }
        if self.document_type:
            vals['l10n_latam_document_type_id'] = self.document_type.id
            vals['l10n_latam_document_number'] = 'F001-00000001'
            
        invoice = self.env['account.move'].create(vals)
        invoice.action_post()
        return invoice

    def register_payment(self, invoice, amount, payment_date):
        # We need to make sure we use the correct payment method line that we handled in setUp
        manual_method = self.env.ref('account.account_payment_method_manual_out')
        payment_method_line = self.journal_bank.outbound_payment_method_line_ids.filtered(lambda l: l.payment_method_id == manual_method)[0]

        payment = self.env['account.payment'].create({
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': invoice.partner_id.id,
            'amount': amount,
            'date': payment_date,
            'journal_id': self.journal_bank.id,
            'payment_method_line_id': payment_method_line.id,
        })
        payment.action_post()
        
        # Reconcile
        lines_to_reconcile = (invoice.line_ids + payment.move_id.line_ids).filtered(
            lambda l: l.account_id == self.account_payable and not l.reconciled
        )
        lines_to_reconcile.reconcile()

    def test_report_cutoff(self):
        """
        Scenario:
        1. Invoice A: 1000. Date: T-60.
        2. Invoice B: 1000. Date: T-60. Payment B: 500 at T-30.
        3. Invoice C: 1000. Date: T-60. Payment C: 1000 at T+10 (Future relative to cutoff T).
        
        Cutoff Date: T (Today)
        
        Expected in Report (Cutoff Today):
        - Invoice A: 1000 Open.
        - Invoice B: 500 Open.
        - Invoice C: 1000 Open (Payment is in future).
        
        Total Balance expected: 2500.
        """
        
        date_t_60 = self.today - timedelta(days=60)
        date_t_30 = self.today - timedelta(days=30)
        date_t_plus_10 = self.today + timedelta(days=10)
        
        # 1. Invoice A: 1000, Unpaid
        inv_a = self.create_invoice(date_t_60, 1000.00)
        
        # 2. Invoice B: 1000, Partial Payment 500 at T-30
        inv_b = self.create_invoice(date_t_60, 1000.00)
        self.register_payment(inv_b, 500.00, date_t_30)
        
        # 3. Invoice C: 1000, Full Payment at T+10 (After Cutoff)
        inv_c = self.create_invoice(date_t_60, 1000.00)
        self.register_payment(inv_c, 1000.00, date_t_plus_10)
        
        # Run Wizard
        wizard = self.env['wizard.report.financial'].create({
            'date_start': self.today - timedelta(days=365),
            'date_end': self.today, # CUTOFF IS TODAY
            'account_ids': [(6, 0, [self.account_payable.id])],
            'seniority_report': False
        })
        
        # Generate Data
        data = wizard.generate_data()
        
        # Assertions
        # 1. Check if data exists for account
        account_key = f"{self.account_payable.code} {self.account_payable.name}"
        self.assertTrue(account_key in data, "Account data not found in report")
        lines = data[account_key]
        
        # 2. Verify Total Balance
        # Expected: 1000 (A) + 500 (B) + 1000 (C, since payment is future) = 2500
        total_balance = sum(l['balance'] for l in lines)
        self.assertAlmostEqual(total_balance, -2500.00, delta=0.01, msg="Total balance incorrect. Payable is Credit, so negative conventionally or positive depending on report logic.") 
        
        # 3. Verify Specific Line Items exist
        # Check Invoice A (Full 1000)
        line_a = next((l for l in lines if l['move'] == inv_a.name), None)
        self.assertTrue(line_a, "Invoice A not found in report")
        self.assertAlmostEqual(line_a['balance'], -1000.00, delta=0.01)

        # Check Invoice B (Partial 500)
        line_b = next((l for l in lines if l['move'] == inv_b.name), None)
        self.assertTrue(line_b, "Invoice B not found in report")
        
        # Check Invoice C (Full 1000 because payment is future)
        line_c = next((l for l in lines if l['move'] == inv_c.name), None)
        self.assertTrue(line_c, "Invoice C not found in report")
        self.assertAlmostEqual(line_c['balance'], -1000.00, delta=0.01)
