from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    reclass_mirror_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Default Reclassification Journal",
        check_company=True,
        ondelete="restrict",
        domain="[('type', '=', 'general')]",
        help="Last resort journal for the reclassification entries of this company, used "
             "when neither the account of the line nor the journal of the bill defines "
             "one.\n\n"
             "Setting it here is enough to make the reclassification work company "
             "wide. Leaving it empty means no reclassification entry is generated unless a more "
             "specific journal is configured; the bill still posts normally.",
    )
