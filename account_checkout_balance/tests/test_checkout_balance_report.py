# -*- coding: utf-8 -*-
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged
from odoo import fields

@tagged('post_install', '-at_install')
class TestCheckoutBalanceReport(TestAccountReportsCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env.ref('account_checkout_balance.checkout_balance_report')

    def test_checkout_balance_generation(self):
        # Create some moves
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2023-01-01',
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 100.0, 'credit': 0.0, 'account_id': self.company_data['default_account_payable'].id}),
                (0, 0, {'debit': 0.0, 'credit': 100.0, 'account_id': self.company_data['default_account_revenue'].id}),
            ],
        })
        move.action_post()

        options = self._generate_options(self.report, '2023-01-01', '2023-12-31')
        lines = self.report._get_lines(options)
        
        # Print lines to debug
        print("\n\nAnalyzed Lines:")
        for line in lines:
            print(line)
        
        self.assertTrue(lines, "Report should return lines")
