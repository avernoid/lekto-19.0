from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from datetime import date

@tagged('post_install', '-at_install')
class TestAddReconcileDate(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data['company']
        cls.account_rcv = cls.company_data['default_account_receivable']
        cls.account_pay = cls.company_data['default_account_payable']
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})

    def test_reconcile_date_calculation(self):
        """ Test that reconcile_date is the maximum date of reconciled lines. """
        
        # 1. Create two invoices on different dates
        inv1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'date': '2024-01-01',
            'invoice_date': '2024-01-01',
            'invoice_line_ids': [(0, 0, {
                'name': 'product test 1',
                'quantity': 1,
                'price_unit': 100.0,
                'account_id': self.company_data['default_account_revenue'].id,
            })],
        })
        inv2 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'date': '2024-02-01',
            'invoice_date': '2024-02-01',
            'invoice_line_ids': [(0, 0, {
                'name': 'product test 2',
                'quantity': 1,
                'price_unit': 100.0,
                'account_id': self.company_data['default_account_revenue'].id,
            })],
        })
        inv1.action_post()
        inv2.action_post()

        # 2. Create a payment on a third date
        payment = self.env['account.payment'].create({
            'amount': 200.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner.id,
            'journal_id': self.company_data['default_journal_bank'].id,
            'date': '2024-03-01',
        })
        payment.action_post()

        # 3. Reconcile them all
        lines_to_reconcile = (inv1 + inv2).line_ids.filtered(lambda l: l.account_id == self.account_rcv)
        lines_to_reconcile += payment.move_id.line_ids.filtered(lambda l: l.account_id == self.account_rcv)
        
        lines_to_reconcile.reconcile()

        # 4. Find the full reconcile record
        full_reconcile = lines_to_reconcile.mapped('full_reconcile_id')
        self.assertTrue(full_reconcile, "A full reconciliation record should have been created.")
        
        # 5. Verify the date: should be the max date (2024-03-01 from the payment)
        expected_date = date(2024, 3, 1)
        self.assertEqual(full_reconcile.reconcile_date, expected_date, 
                         f"Reconcile date should be {expected_date}, got {full_reconcile.reconcile_date}")

    def test_partial_reconcile_no_date(self):
        """ Verify that partial reconciliation doesn't have a full_reconcile record (and thus no date yet). """
        
        inv = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'date': '2024-01-01',
            'invoice_date': '2024-01-01',
            'invoice_line_ids': [(0, 0, {
                'name': 'partial test',
                'quantity': 1,
                'price_unit': 100.0,
                'account_id': self.company_data['default_account_revenue'].id,
            })],
        })
        inv.action_post()

        payment = self.env['account.payment'].create({
            'amount': 50.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner.id,
            'journal_id': self.company_data['default_journal_bank'].id,
            'date': '2024-01-05',
        })
        payment.action_post()

        lines = (inv.line_ids + payment.move_id.line_ids).filtered(lambda l: l.account_id == self.account_rcv)
        lines.reconcile()

        full_reconcile = lines.mapped('full_reconcile_id')
        self.assertFalse(full_reconcile, "Partial reconciliation should not create a full reconciliation record.")
