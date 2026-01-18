from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo import Command, fields
from odoo.exceptions import UserError, RedirectWarning

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from collections import defaultdict

@tagged('post_install', '-at_install')
class TestAccountMove(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        tax_repartition_line = cls.company_data['default_tax_sale'].refund_repartition_line_ids\
            .filtered(lambda line: line.repartition_type == 'tax')
        cls.test_move = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-01-01'),
            'line_ids': [
                (0, None, {
                    'name': 'revenue line 1',
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'debit': 500.0,
                    'credit': 0.0,
                }),
                (0, None, {
                    'name': 'revenue line 2',
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'debit': 1000.0,
                    'credit': 0.0,
                    'tax_ids': [(6, 0, cls.company_data['default_tax_sale'].ids)],
                }),
                (0, None, {
                    'name': 'tax line',
                    'account_id': cls.company_data['default_account_tax_sale'].id,
                    'debit': 150.0,
                    'credit': 0.0,
                    'tax_repartition_line_id': tax_repartition_line.id,
                }),
                (0, None, {
                    'name': 'counterpart line',
                    'account_id': cls.company_data['default_account_expense'].id,
                    'debit': 0.0,
                    'credit': 1650.0,
                }),
            ]
        })
        cls.entry_line_vals_1 = {
            'name': 'Line 1',
            'account_id': cls.company_data['default_account_revenue'].id,
            'debit': 500.0,
            'credit': 0.0,
        }
        cls.entry_line_vals_2 = {
            'name': 'Line 2',
            'account_id': cls.company_data['default_account_expense'].id,
            'debit': 0.0,
            'credit': 500.0,
        }

    def test_compute_invoice_taxes_by_group(self):
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'partner_id': self.partner_a.id,
            'date': fields.Date.from_string('2019-01-01'),
            'currency_id':  self.env['res.currency'].search([('name', '=', 'USD')], limit=1).id,
            'line_ids': [
                (0, None, self.entry_line_vals_1),
                (0, None, self.entry_line_vals_2),
            ],
        })

        move._compute_invoice_taxes_by_group()
        self.assertTrue(move)
        print("---------------- OK ---------------------")