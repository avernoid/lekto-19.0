import base64
from datetime import date

from odoo import models, fields
from ..reports.report_financial import ReportFinancial


class WizardReportFinancial(models.TransientModel):
    _name = 'wizard.report.financial'
    _description = 'Financial report - Wizard'

    date_start = fields.Date(
        string='Start Date',
        required=True,
        help='Start date of the report period. Only affects the report if specific logic requires a range; otherwise, the focus is often on the Cut-off Date (End Date).'
    )
    date_end = fields.Date(
        string='End Date',
        required=True,
        help='Cut-off date for the report. The report will show balances and aging as of this specific date.'
    )
    xls_filename = fields.Char(
        string='File Name',
        help='Name of the generated Excel file.'
    )
    xls_binary = fields.Binary(
        string='Excel Report',
        help='Binary content of the generated Excel report. Click to download.'
    )
    account_ids = fields.Many2many(
        string='Accounts',
        comodel_name='account.account',
        help='Select the Payable or Receivable accounts to analyze in this report.'
    )

    seniority_report = fields.Boolean(
        string='Aging Report',
        default=False,
        help='If checked, the report will include aging columns (e.g., 1-30 days, 31-60 days) to analyze the maturity of debts.'
    )
    target_move = fields.Selection(
        [('posted', 'All Posted Entries'), ('all', 'All Entries')],
        string='Target Moves',
        required=True,
        default='posted'
    )

    def action_generate_excel(self):
        self.ensure_one()
        data = self.generate_data()
        report_financial = ReportFinancial(self, data)
        values_content_xls = report_financial.get_content()
        self.xls_binary = base64.b64encode(values_content_xls)
        self.xls_filename = report_financial.get_filename()
        return self.action_return_wizard()

    def _set_values(self, obj_move_line):
        partner = obj_move_line.partner_id or self.env.company.partner_id
        values = {
            'move_line_id': obj_move_line.id,
            'partner': partner.name,
            'partner_ple': obj_move_line.partner_id.name if obj_move_line.partner_id.name else 'Falso',
            'move': obj_move_line.move_id.name or '',
            'name': obj_move_line.name or '',
            'ref': obj_move_line.ref or '',
            'name_currency': obj_move_line.currency_id.name or '',
            'account_currency': obj_move_line.account_id.currency_id.name or '',
            'date_maturity': obj_move_line.date_maturity or '',
            'vat': partner.vat or '0',
            'vat_ple': obj_move_line.partner_id.vat if obj_move_line.partner_id.vat else '0',
        }

        if 'ple_correlative' in obj_move_line._fields:
            values['ple_correlative'] = obj_move_line.ple_correlative or ''
        if 'l10n_latam_identification_type_id' in partner._fields:
            values['l10n_latam_identification_type_id'] = partner.l10n_latam_identification_type_id or ''

        return values

    def generate_data(self):
        data_account = {}
        target_state = 'posted' if self.target_move == 'posted' else False
        
        for obj_account in self.account_ids:
            name_account = '{} {}'.format(
                obj_account.code,
                obj_account.name
            )
            data_account.setdefault(name_account, [])

            if not obj_account.reconcile:
                domain = [
                    ('account_id', '=', obj_account.id),
                    ('date', '<=', self.date_end)
                ]
                if target_state:
                    domain.append(('parent_state', '=', target_state))
                
                if obj_account.include_initial_balance:
                    list_move_line = self.env['account.move.line'].search(domain, order='id')

                else:
                    domain = [
                        ('account_id', '=', obj_account.id),
                        ('date', '>=', self.date_start),
                        ('date', '<=', self.date_end)
                    ]
                    if target_state:
                        domain.append(('parent_state', '=', target_state))
                    list_move_line = self.env['account.move.line'].search(domain, order='id')

                if list_move_line:
                    sum_balance = sum(map(lambda x: x.balance, list_move_line))
                    sum_currency = sum(map(lambda x: x.amount_currency, list_move_line))
                    values = {
                        'date': date.strftime(self.date_end, '%d/%m/%Y'),
                        'balance': sum_balance,
                        'account': obj_account.code,
                        'amount_currency': sum_currency
                    }
                    values.update(self._set_values(list_move_line[0]))
                    data_account[name_account].append(values)

            else:
                list_full_reconcile = self.env['account.full.reconcile'].search([
                    ('reconcile_date', '>', self.date_end)
                ])
                domain = [
                    ('account_id', '=', obj_account.id),
                    ('date', '<=', self.date_end)
                ]
                if target_state:
                    domain.append(('parent_state', '=', target_state))
                list_move_line = self.env['account.move.line'].search(domain, order='id')

                list_ml_reconcile = list_move_line.filtered(lambda x: x.full_reconcile_id in list_full_reconcile)
                list_ml_zero = list_move_line.filtered(lambda x: not x.full_reconcile_id and not x.matched_debit_ids and not x.matched_credit_ids)

                list_ml_unreconcile = list_move_line.filtered(lambda x: not x.full_reconcile_id)
                list_ml_unreconcile_filter = []
                for _item in list_ml_unreconcile:
                    if _item not in list_ml_zero:
                        list_ml_unreconcile_filter.append(_item)

                if list_ml_reconcile:
                    dict_group = {}
                    for obj_ml in list_ml_reconcile:
                        reconcile_date = obj_ml.full_reconcile_id.reconcile_date
                        values = {
                            'date': date.strftime(obj_ml.date, '%d/%m/%Y'),
                            'balance': 0.00,
                            'account': obj_account.code,
                            'amount_currency': 0.00,
                            'date_maturity': obj_ml.date_maturity or '',
                            'date_reconcile': date.strftime(reconcile_date, '%d/%m/%Y'),
                            'reconcile': obj_ml.full_reconcile_id.display_name,
                        }
                        values.update(self._set_values(obj_ml))
                        dict_group.setdefault(obj_ml.full_reconcile_id.id, values)
                        dict_group[obj_ml.full_reconcile_id.id]['balance'] += obj_ml.balance
                        dict_group[obj_ml.full_reconcile_id.id]['amount_currency'] += obj_ml.amount_currency
                    data_account[name_account].extend(map(lambda x: dict_group[x], dict_group.keys()))
                if list_ml_unreconcile_filter:
                    list_unreconcile_ml = []
                    dict_temporal = {}

                    # Optimization 1: Filter partial reconciliations by relevant move lines
                    unreconciled_ids = [line.id for line in list_ml_unreconcile_filter]
                    domain_partial = [
                        ('full_reconcile_id', '=', False),
                        '|',
                        ('debit_move_id', 'in', unreconciled_ids),
                        ('credit_move_id', 'in', unreconciled_ids)
                    ]
                    list_obj_partial_reconcile = self.env['account.partial.reconcile'].search(domain_partial, order='max_date')

                    # Optimization 2: Use Sets for O(1) lookups
                    unreconciled_ids_set = set(unreconciled_ids)

                    for obj_reconcile in list_obj_partial_reconcile:
                        obj_ml1 = False
                        obj_ml2 = False
                        bool_exist = False
                        
                        if obj_reconcile.debit_move_id.id in unreconciled_ids_set:
                            obj_ml1 = obj_reconcile.debit_move_id
                        if obj_reconcile.credit_move_id.id in unreconciled_ids_set:
                            obj_ml2 = obj_reconcile.credit_move_id

                        list_item = (obj_ml1, obj_ml2) if obj_ml1 and obj_ml2 else obj_ml1 if obj_ml1 else obj_ml2 if obj_ml2 else ()
                        e = False
                        for i in range(len(list_unreconcile_ml)):
                            if obj_ml1 in list_unreconcile_ml[i] or obj_ml2 in list_unreconcile_ml[i]:
                                if not bool_exist:
                                    bool_exist = True
                                    dict_temporal.update({
                                        i: list_unreconcile_ml[i]
                                    })
                                    list_unreconcile_ml[i].extend(list(list_item))
                                    dict_temporal[i].extend(list(list_item))
                                    e = i
                                else:
                                    if e:
                                        dict_temporal[e].extend(list_unreconcile_ml[i])
                                        if dict_temporal.get(i):
                                            del dict_temporal[i]

                        if not bool_exist:
                            list_value = []
                            if obj_ml1:
                                list_value.append(obj_ml1)
                            if obj_ml2:
                                list_value.append(obj_ml2)
                            if list_value:
                                list_unreconcile_ml.append(list_value)
                                dict_temporal.update({len(list_unreconcile_ml) - 1: list_value})

                    list_unreconcile_set = [list(set(dict_temporal[key])) for key in dict_temporal]
                    for list_ml in list_unreconcile_set:
                        data_d = {
                            'date': date.strftime(list_ml[0].date, '%d/%m/%Y'),
                            'balance': 0.00,
                            'amount_currency': 0.00,
                            'move_line_id': list_ml[0].id,
                            'account': obj_account.code
                        }
                        data_d.update(self._set_values(list_ml[0]))
                        for i in range(len(list_ml)):
                            data_d['balance'] += list_ml[i].balance
                            data_d['amount_currency'] += list_ml[i].amount_currency
                            if data_d['move_line_id'] > list_ml[i].id:
                                data_d.update({
                                    'date': date.strftime(list_ml[i].date, '%d/%m/%Y'),
                                    'move_line_id': list_ml[i].id,
                                })
                                data_d.update(self._set_values(list_ml[i]))
                        data_account[name_account].append(data_d)
                for obj_ml_zero in list_ml_zero:
                    values = {
                        'date': date.strftime(obj_ml_zero.date, '%d/%m/%Y'),
                        'balance': obj_ml_zero.balance,
                        'amount_currency': obj_ml_zero.amount_currency,
                        'account': obj_account.code,
                    }
                    values.update(self._set_values(obj_ml_zero))
                    data_account[name_account].append(values)
        return data_account

    def action_return_wizard(self):
        wizard_form_id = self.env.ref('financial_statement_annexes.wizard_report_financial_view_form').id
        return {
            'type': 'ir.actions.act_window',
            # [V19 Migration] Removed deprecated view_type
            # 'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.report.financial',
            'views': [(wizard_form_id, 'form')],
            'view_id': wizard_form_id,
            'res_id': self.id,
            'target': 'new'
        }
