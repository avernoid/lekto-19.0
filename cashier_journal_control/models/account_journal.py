from odoo import models, fields

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    allowed_user_ids = fields.Many2many(
        'res.users',
        string='Allowed Users',
        help="Users allowed to use this journal in the payment register wizard. "
             "If empty, all users can use it."
    )
    is_default_cash = fields.Boolean(
        string='Default Cash',
        help="If checked, this journal will be proposed as the default journal "
             "in the payment register wizard for the allowed users. "
             "If multiple journals are marked, the one with the lowest sequence is used."
    )
