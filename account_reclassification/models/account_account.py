from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountAccount(models.Model):
    """Reclassification setup of a chart account.

    Every field here is **company dependent**, like the native valuation accounts
    of ``product.category``. The chart of accounts is shared between companies
    through ``company_ids``, so a single global value could not serve two of them:
    the second company would book its entry against the journal and the accounts
    of the first, the company constraint would reject the entry, and the bill
    would post without it. Each company configures the same shared account on its
    own, and ``check_company`` validates each value against the company that owns
    it.
    """

    _inherit = "account.account"

    reclass_mirror_mode = fields.Selection(
        selection=[
            ("none", "Do not create"),
            ("journal", "Create if the journal allows it"),
            ("always", "Always create"),
        ],
        string="Reclassification Entry",
        default="none",
        company_dependent=True,
        help="Decides whether a vendor bill line posted on this account also produces "
             "the reclassification entry, which is a SEPARATE journal "
             "entry: the bill itself is never modified.\n\n"
             "Do not create: this account never produces a reclassification entry. This is the "
             "default, so installing the module changes nothing until you configure "
             "it.\n\n"
             "Create if the journal allows it: the reclassification entry is generated only when "
             "the journal of the bill has 'Generate Reclassification Entry' ticked. Use it "
             "to enable the reclassification journal by journal.\n\n"
             "Always create: having this account on the line is enough, whatever the "
             "journal setting. Use it for accounts that must always be reclassified.\n\n"
             "Set per company: on an account shared between companies, each one "
             "decides on its own.",
    )
    reclass_target_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Target Account",
        company_dependent=True,
        check_company=True,
        ondelete="restrict",
        help="Account that represents this one on the reclassification entry, by nature "
             "(e.g. 60 Compras).\n\n"
             "It always keeps the side of the mirrored line: it is debited when the "
             "bill line is debited, and credited on a vendor credit note. Required as "
             "soon as the mode is not 'Do not create'.\n\n"
             "Set per company, and it must belong to the company setting it.",
    )
    reclass_counterpart_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Counterpart Account",
        company_dependent=True,
        check_company=True,
        ondelete="restrict",
        help="Account that balances the reclassification entry (e.g. 61 Variacion de "
             "existencias).\n\n"
             "It always takes the side opposite to the target account, so the entry is "
             "balanced and has no net effect on the result. It must be different from "
             "the target account, otherwise the entry would have no effect.\n\n"
             "Set per company, and it must belong to the company setting it.",
    )
    reclass_mirror_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Reclassification Journal",
        company_dependent=True,
        check_company=True,
        ondelete="restrict",
        domain="[('type', '=', 'general')]",
        help="Journal receiving the reclassification entries generated from this account. This "
             "is the most specific level and wins over any other setting.\n\n"
             "When empty, the journal set on the journal of the bill is used, and "
             "failing that the company default defined in the accounting settings. If "
             "none of the three is set, no reclassification entry is generated: the bill still "
             "posts normally and the manual button explains what is missing.\n\n"
             "Set per company, and it must belong to the company setting it.",
    )

    @api.constrains("reclass_mirror_mode", "reclass_target_account_id", "reclass_counterpart_account_id")
    def _check_reclass_mirror_accounts(self):
        # Company dependent fields are read for ``self.env.company``, so this
        # validates the setup of the company doing the write, which is the only
        # one it can be writing.
        for account in self:
            if account.reclass_mirror_mode == "none":
                continue
            if not account.reclass_target_account_id or not account.reclass_counterpart_account_id:
                raise ValidationError(_(
                    "Account %(account)s generates a reclassification entry for company "
                    "%(company)s, so it needs both a target and a counterpart account "
                    "for that company.",
                    account=account.display_name,
                    company=self.env.company.display_name,
                ))
            if account.reclass_target_account_id == account.reclass_counterpart_account_id:
                raise ValidationError(_(
                    "The target and the counterpart of the reclassification entry of "
                    "%(account)s must be two different accounts, otherwise the entry "
                    "has no effect.",
                    account=account.display_name,
                ))

    @api.onchange("reclass_mirror_mode")
    def _onchange_reclass_mirror_mode(self):
        if self.reclass_mirror_mode == "none":
            self.reclass_target_account_id = False
            self.reclass_counterpart_account_id = False
            self.reclass_mirror_journal_id = False
