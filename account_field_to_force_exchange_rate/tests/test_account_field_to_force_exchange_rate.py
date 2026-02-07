from odoo.tests import TransactionCase, tagged
from odoo import fields

@tagged('post_install', '-at_install')
class TestAccountFieldToForceExchangeRate(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # 1. Setup Currency environment
        cls.currency_pen = cls.env.ref('base.PEN') # Assuming PEN is base
        cls.currency_usd = cls.env.ref('base.USD')
        
        # Ensure company base is PEN for testing physics
        cls.env.company.currency_id = cls.currency_pen
        
        # 2. Setup Exchange Rates
        # Scenario: 1 USD = 4.0 PEN.
        # Check if rate is "Direct" or "Indirect". Odoo default is Indirect (1 unit of currency = X units of base).
        # Actually Odoo default is "1 unit of base = X units of currency" (Indirect).
        # BUT 'rate' field in res.currency.rate stores (1 / direct_rate).
        # So for 4.0 PEN/USD: Rate = 0.25.
        cls.todays_rate = 0.25
        
        cls.env['res.currency.rate'].create({
            'currency_id': cls.currency_usd.id,
            'name': fields.Date.today(),
            'rate': cls.todays_rate, 
            'company_id': cls.env.company.id,
        })
        
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})
        cls.account_receivable = cls.partner.property_account_receivable_id
        cls.journal_bank = cls.env['account.journal'].search([('type', '=', 'bank')], limit=1)

    def test_01_manual_entry_safeguard(self):
        """Test that forcing 'invoice_currency_rate' on a Manual Entry correctly overrides the line rate."""
        # Force rate to 0.5 (1 USD = 2.0 PEN). System default is 0.25 (1 USD = 4.0 PEN).
        forced_rate = 0.5
        
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.today(),
            'journal_id': self.env['account.journal'].search([('type', '=', 'general')], limit=1).id,
            'currency_id': self.currency_usd.id,
            'invoice_currency_rate': forced_rate, # Explicitly forcing
            'line_ids': [
                (0, 0, {
                    'name': 'Debit USD',
                    'account_id': self.account_receivable.id,
                    'debit': 200.0, # 200 PEN
                    'credit': 0.0,
                    'amount_currency': 100.0, # 100 USD. Implies Rate 0.5 (200 * 0.5 = 100)
                    'currency_id': self.currency_usd.id,
                }),
                (0, 0, {
                    'name': 'Credit USD',
                    'account_id': self.account_receivable.id,
                    'debit': 0.0,
                    'credit': 200.0,
                    'amount_currency': -100.0,
                    'currency_id': self.currency_usd.id,
                }),
            ]
        })
        move.action_post()
        
        # Verify Safeguard worked: Line should use 0.5, NOT the system 0.25
        line = move.line_ids.filtered(lambda l: l.amount_currency == 100.0)
        self.assertEqual(line.currency_rate, forced_rate, "Safeguard failed: Line did not use forced rate for Entry.")

    def test_02_manual_payment_defaults(self):
        """Test that creating a Manual Payment defaults to the system rate (Auto-Complete logic)."""
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'amount': 100.0,
            'currency_id': self.currency_usd.id,
            'partner_id': self.partner.id,
            'journal_id': self.journal_bank.id,
        })
        
        # Should default to today's rate (0.25)
        self.assertAlmostEqual(payment.to_force_exchange_rate, self.todays_rate, places=4, 
            msg="Auto-complete logic failed: Did not pull system rate.")

    def test_03_payment_to_entry_precedence(self):
        """Test the critical path: Manual Payment with Forced Rate -> Journal Entry."""
        # Force 0.1 (1 USD = 10 PEN)
        forced_rate = 0.1 
        
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'amount': 100.0,
            'currency_id': self.currency_usd.id,
            'partner_id': self.partner.id,
            'journal_id': self.journal_bank.id,
            'to_force_exchange_rate': forced_rate, # User overrides default
        })
        payment.action_post()
        
        # Verify linkage
        move = payment.move_id
        self.assertTrue(move, "Payment did not create a move.")
        
        # Verify Precedence Logic in account_move.py
        self.assertEqual(move.invoice_currency_rate, forced_rate, 
            "Move header did not inherit payment forced rate.")
            
        # Verify Line Safeguard
        line = move.line_ids.filtered(lambda l: l.account_id == self.account_receivable)
        # Note: Depending on payment direction, line might be debit or credit.
        # Just check the rate used.
        self.assertEqual(line.currency_rate, forced_rate, 
            "Move lines did not respect the forced rate propagated from payment.")
            
        # CRITICAL ASSERTION (Previously Missing)
        # Verify that the Debit/Credit/Balance is actually calculated using the forced rate.
        # Formula: Balance = AmountCurrency * ForcedRate
        # 100.0 USD * 0.1 = 10.0 PEN
        expected_balance = 100.0 * forced_rate
        # Wait, Inbound Payment:
        # Bank (Debit) 10
        # Receivable (Credit) 10
        
        # We are checking the receivable line (cls.account_receivable).
        # It should        # NATIVE LOGIC EXPECTATION:
        # Input Rate: 0.1 (Indirect).
        # Amount: 100 USD.
        # Math: 100 / 0.1 = 1000 PEN.
        expected_balance = 1000.0
        self.assertAlmostEqual(abs(line.balance), expected_balance, places=2,
            msg=f"Accounting Logic Fail: Expected balance {expected_balance} (100 / {forced_rate}) but got {abs(line.balance)}. Pre-calculation override might be missing.")
