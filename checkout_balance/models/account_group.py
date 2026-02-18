from odoo import models, fields


class AccountGroup(models.Model):
    _inherit = 'account.group'

    type_group = fields.Selection(
        selection=[
            ('balance', 'Balance'),
            ('function', 'Income by Function'),
            ('nature', 'Income by Nature'),
            ('both', 'Both Incomes')
        ],
        string='Group Type',
        help='Determines where the account group balances are displayed in the Checkout Balance report:\n'
             '- Balance: Shown in the "General Balance" column (Assets/Liabilities).\n'
             '- Income by Function: Shown in the "EERR by Function" column.\n'
             '- Income by Nature: Shown in the "EERR by Nature" column.\n'
             '- Both Incomes: Shown in both "EERR by Function" and "EERR by Nature" columns.'
    )
