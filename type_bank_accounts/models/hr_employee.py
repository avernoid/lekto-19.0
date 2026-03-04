from odoo import api, fields, models


class HrEmployeeTypeBankAccount(models.Model):
    _inherit = 'hr.employee'

    account_salary_bank = fields.Char(
        string='Salary Account',
        readonly=True,
        compute='_compute_select_information_partner',
        help=(
            'Auto-computed field. Displays the account number of the bank account '
            'classified as "Salary" (acc_type = wage) linked to this employee\'s work contact. '
            'This field updates automatically when the employee\'s bank accounts are saved. '
            'To change this value, update the corresponding bank account record and set its '
            'Account Type to "Salary".'
        ),
    )
    type_salary_bank = fields.Char(
        string='Salary Bank',
        readonly=True,
        compute='_compute_select_information_partner',
        help=(
            'Auto-computed field. Displays the name of the bank associated with the account '
            'classified as "Salary" (acc_type = wage) for this employee. '
            'This field updates automatically when the employee\'s bank accounts are saved. '
            'The bank name is pulled from the bank record linked to the salary bank account.'
        ),
    )
    account_cts_bank = fields.Char(
        string='CTS Account',
        readonly=True,
        compute='_compute_select_information_partner',
        help=(
            'Auto-computed field. Displays the account number of the bank account '
            'classified as "CTS" (acc_type = cts) linked to this employee\'s work contact. '
            'CTS stands for Compensación por Tiempo de Servicios — a mandatory severance benefit '
            'in Peru. This field updates automatically when bank accounts are saved.'
        ),
    )
    type_cts_bank = fields.Char(
        string='CTS Bank',
        readonly=True,
        compute='_compute_select_information_partner',
        help=(
            'Auto-computed field. Displays the name of the bank associated with the account '
            'classified as "CTS" (acc_type = cts) for this employee. '
            'This field updates automatically when the employee\'s bank accounts are saved. '
            'The bank name is pulled from the bank record linked to the CTS bank account.'
        ),
    )

    @api.depends('bank_account_ids')
    def _compute_select_information_partner(self):
        for employee in self:
            res_partner_bank = employee.env['res.partner.bank'].search([
                ('partner_id', '!=', False),
                ('partner_id.id', '=', employee.work_contact_id.id),
            ])
            account_salary_bank_employee = ''
            type_salary_bank_employee = ''
            account_cts_bank_employee = ''
            type_cts_bank_employee = ''
            for res in res_partner_bank:
                if res.acc_type == 'wage':
                    account_salary_bank_employee = res.acc_number
                    type_salary_bank_employee = res.bank_id.name
                if res.acc_type == 'cts':
                    account_cts_bank_employee = res.acc_number
                    type_cts_bank_employee = res.bank_id.name
            for result in employee:
                result.account_salary_bank = account_salary_bank_employee or ''
                result.type_salary_bank = type_salary_bank_employee or ''
                result.account_cts_bank = account_cts_bank_employee or ''
                result.type_cts_bank = type_cts_bank_employee or ''