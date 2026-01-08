# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged
from datetime import date, timedelta


@tagged('post_install', '-at_install')
class TestFinancialCurrencyLogic(TransactionCase):

    def setUp(self):
        super(TestFinancialCurrencyLogic, self).setUp()
        
        # 1. Setup Currency (Foreign) and Rates
        # We allow company to be USD. We create a foreign currency 'TESTC'
        self.company_currency = self.env.company.currency_id
        
        self.currency_foreign = self.env['res.currency'].create({
            'name': 'TESTC',
            'symbol': 'T',
            'rounding': 0.01,
            'active': True,
        })
        
        # Ensure rates: 1 TESTC = 1.0 Company Currency
        self.env['res.currency.rate'].create({
            'name': date.today(),
            'rate': 1.0,
            'currency_id': self.currency_foreign.id,
            'company_id': self.env.company.id,
        })

        # 2. Setup Accounts for Gain/Loss (Critical for Wizard)
        self.account_gain = self.env['account.account'].create({
            'name': 'Gain Account',
            'code': 'TESTGAIN998',
            'account_type': 'income',
            'reconcile': False,
        })
        self.account_loss = self.env['account.account'].create({
            'name': 'Loss Account',
            'code': 'TESTLOSS999',
            'account_type': 'expense',
            'reconcile': False,
        })
        
        self.env.company.write({
            'income_currency_exchange_account_id': self.account_gain.id,
            'expense_currency_exchange_account_id': self.account_loss.id,
        })

        # 3. Setup Bank Account in USD
        self.account_usd = self.env['account.account'].create({
            'name': 'Bank Foreign',
            'code': 'TESTFOR101',
            'account_type': 'asset_cash',
            'currency_id': self.currency_foreign.id,
            'reconcile': False,
        })
        
        self.journal_foreign = self.env['account.journal'].create({
            'name': 'Bank Foreign',
            'type': 'bank',
            'code': 'TBF',
            'currency_id': self.currency_foreign.id,
            'default_account_id': self.account_usd.id,
        })
        
        # 4. Setup Exchange Difference Journal (REQUIRED for Wizard)
        self.journal_exchange = self.env['account.journal'].create({
            'name': 'Exchange Difference',
            'type': 'general',
            'code': 'TSTEX',
            'currency_id': self.company_currency.id,
        })
        
        self.env.company.write({
            'currency_exchange_journal_id': self.journal_exchange.id,
        })

    def test_unrealized_gain_calculation(self):
        """ Test calculation of unrealized gain when rate increases """
        
        # A. Create Initial Move: 1000 USD at Rate 1.0 = 1000 Company Currency
        # We manually create a move to simulate a balance
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': date.today(),
            'journal_id': self.journal_foreign.id,
            'line_ids': [
                (0, 0, {
                    'name': 'Initial Balance',
                    'debit': 1000.0,
                    'credit': 0.0,
                    'account_id': self.account_usd.id,
                    'amount_currency': 1000.0,
                    'currency_id': self.currency_foreign.id,
                }),
                (0, 0, {
                    'name': 'Counterpart',
                    'debit': 0.0,
                    'credit': 1000.0,
                    'account_id': self.account_gain.id, # Using gain account as dummy counterpart
                    'amount_currency': -1000.0,
                    'currency_id': self.currency_foreign.id,
                }),
            ]
        })
        move.action_post()
        
        # B. Run Wizard
        # Scenario: Closing Rate is 1.2 (Gain of 0.2 per USD)
        # Expected New Balance in Company Currency = 1000 USD * 1.2 = 1200
        # Valid Balance in Company Currency = 1000
        # Adjustment = 1200 - 1000 = 200 (Debit to Bank, Credit to Gain)
        
        wizard = self.env['wizard.report.financial.currency'].create({
            'date_start': date.today(),
            'date_end': date.today(),
            'company_id': self.env.company.id,
            'currency_id': self.currency_foreign.id, # Filter
            'account_ids': [(6, 0, [self.account_usd.id])]
        })
        
        # Simulate setting the Closing Rate in the wizard line
        self.account_usd.write({'adjustment_rate': 1.2})
        
        # C. Generate Adjustment Entry
        wizard.generate_thing()
        
        # D. Validate Result
        # Search for adjustment move
        adj_move = self.env['account.move'].search([
            ('ref', '=', 'Ajuste diferencia cambio No realizada'),
            ('date', '=', date.today())
        ], limit=1)
        
        self.assertTrue(adj_move, "Adjustment Move was not created")
        self.assertEqual(adj_move.state, 'posted', "Adjustment move should be posted")
        
        # Check Lines
        # We expect a Debit on Bank USD of 200.0 (Difference)
        bank_line = adj_move.line_ids.filtered(lambda l: l.account_id == self.account_usd)
        self.assertAlmostEqual(bank_line.debit, 200.0, delta=0.01, msg="Debit adjustment should be 200.0")
        self.assertAlmostEqual(bank_line.amount_currency, 0.0, msg="Amount currency should be 0 for revaluation")
        
        # Check Counterpart
        gain_line = adj_move.line_ids.filtered(lambda l: l.account_id == self.account_gain)
        self.assertAlmostEqual(gain_line.credit, 200.0, delta=0.01, msg="Credit to Gain account should be 200.0")

        # E. Validate Reversal
        # Reversal should be created for next day
        reversal_move = self.env['account.move'].search([
            ('ref', 'like', 'Reversión: ' + adj_move.ref),
            ('date', '=', date.today() + timedelta(days=1))  # Logic says date_end + 1 day
        ], limit=1)
        
        self.assertTrue(reversal_move, "Reversal move was not created")
        self.assertEqual(reversal_move.state, 'draft', "Reversal move is usually draft or posted (logic does not post reversal automatically in all versions, checking state)")
