from odoo import api, fields, models


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    @api.model
    def _get_supported_account_types(self):
        return [
            ('bank', 'Normal'),
            ('wage', 'Salary'),
            ('cts', 'CTS'),
            ('other', 'Others'),
        ]

    acc_type = fields.Selection(
        selection=lambda x: x.env['res.partner.bank']._get_supported_account_types(),
        default='bank',
        string='Account Type',
        help=(
            'Classifies the purpose of this bank account for payroll processing:\n'
            '- Normal: General-purpose bank account (default). Does not affect computed payroll fields.\n'
            '- Salary: Used for monthly wage disbursements. When set, this account number and bank name '
            'will be automatically reflected on the employee form under the Payments section.\n'
            '- CTS: Designated for CTS (Compensación por Tiempo de Servicios) deposits. When set, '
            'this account number and bank name will be automatically reflected on the employee form.\n'
            '- Others: Catch-all for special-purpose accounts not covered by the above types.'
        ),
        compute=False,
        required=False,
    )
    type_bank_code = fields.Char(
        string='Type Code',
        help=(
            'Internal classification or branch code assigned by the bank to this account. '
            'Commonly used in LatAm banking systems to identify the account type or the branch. '
            'Fill this field if your payroll or banking integration requires a bank-specific code '
            'alongside the account number.'
        ),
    )
    cci = fields.Char(
        string='CCI',
        help=(
            'Código de Cuenta Interbancaria (Inter-bank Account Code). '
            'A standardized 20-digit code used in Peru and other LatAm countries to uniquely '
            'identify a bank account across different financial institutions. '
            'Required for inter-bank transfers. Leave blank if not applicable.'
        ),
    )
