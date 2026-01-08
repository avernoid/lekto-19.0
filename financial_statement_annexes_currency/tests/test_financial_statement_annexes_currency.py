from odoo.tests import TransactionCase
from datetime import date
# [V19 Migration] Tests reviewed for deprecated methods.


class TestWizardReportFinancial(TransactionCase):

    def setUp(self):
        super(TestWizardReportFinancial, self).setUp()
        self.wizard_report_financial = self.env['wizard.report.financial.currency']

    def test_generate_data(self):
        date_start = date.today()
        date_end = date.today()
        account_ids = self.env['account.account'].search([], limit=5)

        wizard = self.wizard_report_financial.create({
            'date_start': date_start,
            'date_end': date_end,
            'account_ids': [(6, 0, account_ids.ids)],
        })

        data = wizard.generate_data()

        self.assertTrue(isinstance(data, dict))
        print('------------TEST OK ----------')

    def test_action_generate_excel(self):
        date_start = date.today()
        date_end = date.today()
        account_ids = self.env['account.account'].search([], limit=5)

        wizard = self.wizard_report_financial.create({
            'date_start': date_start,
            'date_end': date_end,
            'account_ids': [(6, 0, account_ids.ids)],
        })

        wizard.action_generate_excel()

        self.assertTrue(wizard.xls_binary)
        print('------------TEST OK ------------')

    def test_action_return_wizard(self):
        date_start = date.today()
        date_end = date.today()
        account_ids = self.env['account.account'].search([], limit=5)

        wizard = self.wizard_report_financial.create({
            'date_start': date_start,
            'date_end': date_end,
            'account_ids': [(6, 0, account_ids.ids)],
        })

        result = wizard.action_return_wizard()

        self.assertTrue(result)
        print('------------TEST OK ----------')