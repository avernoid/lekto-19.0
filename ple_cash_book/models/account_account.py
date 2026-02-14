from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    ple_selection = fields.Selection(
        selection_add=[
            ("cash", "1.1 Cash & Bank Book: Cash"),
            ("bank", "1.2 Cash & Bank Book: Bank Accounts"),
        ],
    )
    bank_id = fields.Many2one(
        comodel_name='res.partner.bank',
        string='Bank Account',
        help="Link this account to a bank account. The bank's SUNAT code (l10n_pe_edi_code) "
             "will be used in the PLE Bank report (TXT 1.2). Only relevant for accounts "
             "of type 'Cash and Bank Accounts' (asset_cash).",
    )
