from odoo.tests import TransactionCase


class TestCheckoutBalanceCustomHandler(TransactionCase):

    def setUp(self):
        super(TestCheckoutBalanceCustomHandler, self).setUp()
        self.report = self.env['account.report'].create({
            'name': 'Test Report',
            #'report_type': 'account',
            'line_ids': [],
        })
        self.handler = self.env['account.checkout.balance.report.handler']
        print("<<<<<<SETUP>>>>>>")     
        

    def test_caret_options_initializer(self):
        caret_options = self.handler._caret_options_initializer()
        self.assertIn('checkout_balance_account_group', caret_options)
        self.assertIn('checkout_balance_account_account', caret_options)
        print("<<<<< TEST CARET OPTION >>>>>>")

    def test_custom_options_initializer(self):
        options = {
            'date': {
                'date_from': '2023-01-01',
                'date_to': '2023-12-31'
            },
            'column_headers': [['Header 1', 'Header 2']],
            'columns': [{'column_label': 'initial_column', 'column_group_key': 'group1'}],
            'column_groups': {},
            'comparison': {
                'periods': [{'date_from': '2023-01-01', 'date_to': '2023-12-31'}]
            }
        }
        previous_options = {}
        self.handler._custom_options_initializer(self.report, options, previous_options)        
        self.assertIn('initial_column', [col['column_label'] for col in options['columns']])
        print("<<<<<<< TEST CUSTOM OPTIONS INITIALIZER >>>>>>> ")


