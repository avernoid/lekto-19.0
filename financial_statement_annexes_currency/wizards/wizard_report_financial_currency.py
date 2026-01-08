import base64
from datetime import timedelta

from odoo import models, fields, _
from odoo.exceptions import UserError
from ..reports.report_financial import ReportFinancial


class WizardReportFinancialCurrency(models.TransientModel):
    _name = 'wizard.report.financial.currency'
    _description = 'Financial report currency - Wizard'

    date_start = fields.Date(
        string='Start Date',
        required=True,
        help="Start date of the analysis period."
    )
    date_end = fields.Date(
        string='End Date',
        required=True,
        help="End date of the analysis period."
    )
    xls_filename = fields.Char()
    xls_binary = fields.Binary('Excel Report', help="Generated Excel report file.")
    company_id = fields.Many2one('res.company', store=True, readonly=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, related="company_id.currency_id")

    account_ids = fields.Many2many(
        string='Accounts',
        comodel_name='account.account',
        help="Select the foreign currency accounts to analyze."
    )
    seniority_report = fields.Boolean('Aging Report', default=False, help="Include aging analysis in the report.")

    def generate_data(self):
        wizard = self.env['wizard.report.financial'].create({
            'date_start': self.date_start,
            'date_end': self.date_end,
            'account_ids': self.account_ids,
        })
        data = wizard.generate_data()
        adjustment_rate = [account.adjustment_rate for account in self.account_ids]
        for enum, k in enumerate(data.keys()):
            values = {
                'adjustment_rate': adjustment_rate[enum]
            }
            if data[k]:
                for line_data in data[k]:
                    line_data.update(values)

        return data

    def action_generate_excel(self):
        self.ensure_one()

        data = self.generate_data()
        report_financial = ReportFinancial(self, data)
        values_content_xls = report_financial.get_content()
        self.xls_binary = base64.b64encode(values_content_xls)
        self.xls_filename = report_financial.get_filename()
        return self.action_return_wizard()

    def generate_thing(self):
        currency_exchange_journal_id = self.company_id.currency_exchange_journal_id.id
        if not currency_exchange_journal_id:
            raise UserError(_("Please configure the 'Currency Exchange Journal' in Accounting Settings -> Currencies."))
            
        cap_journal = self.env['account.journal'].search([('id', '=', currency_exchange_journal_id)]).id

        data = self.generate_data()
        account_ids = [account for account in self.account_ids]

        income_currency_exchange_account_id = self.company_id.income_currency_exchange_account_id.id
        expense_currency_exchange_account_id = self.company_id.expense_currency_exchange_account_id.id
        account_gain = self.env['account.account'].search([('id', '=', income_currency_exchange_account_id)]).id
        account_lose = self.env['account.account'].search([('id', '=', expense_currency_exchange_account_id)]).id

        line_ids = []

        for enum, k in enumerate(data.keys()):
            if data[k]:
                sum_adjust = 0.00
                for line_data in data[k]:
                    amount_currency = line_data.get('balance', 0.00) if not line_data.get(
                        'account_currency') else line_data.get('amount_currency', 0.00)
                    updated_balance = amount_currency * line_data.get('adjustment_rate', 0.00)
                    adjust = updated_balance - line_data.get('balance', 0.00)
                    sum_adjust += adjust

                debit = abs(sum_adjust) if sum_adjust >= 0.00 else 0.00
                credit = abs(sum_adjust) if sum_adjust < 0.00 else 0.00

                line_1 = (
                    0, 0, {
                        'name': 'Ajuste diferencia cambio No realizada',
                        'debit': debit,
                        'credit': credit,
                        'account_id': account_ids[enum].id,
                        'currency_id': account_ids[enum].currency_id.id,
                        'amount_currency': 0.0
                    }
                )
                line_2 = (
                    0, 0, {
                        'name': 'Ajuste diferencia cambio No realizada',
                        'debit': credit,
                        'credit': debit,
                        'account_id': account_gain if sum_adjust >= 0.00 else account_lose,
                        'currency_id': account_ids[enum].currency_id.id,
                        'amount_currency': 0.0,
                    }
                )
                line_ids.append(line_1)
                line_ids.append(line_2)

        account_move = self.env['account.move'].create({
            'state': 'draft',
            'ref': 'Ajuste diferencia cambio No realizada',
            'date': self.date_end,
            'journal_id': cap_journal,
            'line_ids': line_ids,
        })

        account_move.action_post()

        reverse_move = account_move._reverse_moves(
            default_values_list=[{
                'date': self.date_end + timedelta(days=1),
                'ref': 'Reversión: ' + account_move.ref,
            }],
            cancel=False,
        )

        return self.action_return_wizard()

    def action_return_wizard(self):
        wizard_form_id = self.env.ref(
            'financial_statement_annexes_currency.wizard_report_financial_currency_view_form').id
        return {
            'type': 'ir.actions.act_window',
            # [V19 Migration] Removed deprecated view_type
            'view_mode': 'form',
            'res_model': 'wizard.report.financial.currency',
            'views': [(wizard_form_id, 'form')],
            'view_id': wizard_form_id,
            'res_id': self.id,
            'target': 'new'
        }
