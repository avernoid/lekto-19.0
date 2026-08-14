from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    generate_reclass_mirror = fields.Boolean(
        string="Generate Reclassification Entry",
        help="Enables the reclassification for the bills of this journal.\n\n"
             "Ticked: every bill line whose account is set to 'Create if the journal "
             "allows it' produces its reclassification entry.\n\n"
             "Unticked: those lines are skipped and the bill posts exactly as without "
             "this module. Accounts set to 'Always create' ignore this checkbox and "
             "are mirrored either way.",
    )
    reclass_mirror_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Reclassification Journal",
        check_company=True,
        ondelete="restrict",
        domain="[('type', '=', 'general')]",
        help="Dedicated journal holding the reclassification entries generated from the "
             "bills of this journal (e.g. 'Accounting Reclassification'). Keeping them "
             "in their own journal leaves your purchase journal untouched.\n\n"
             "The journal set on the account of the line wins over this one; when "
             "neither is set, the company default from the accounting settings is "
             "used.",
    )
