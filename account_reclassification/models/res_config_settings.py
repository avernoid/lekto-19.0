from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    reclass_mirror_journal_id = fields.Many2one(
        related="company_id.reclass_mirror_journal_id",
        string="Default Reclassification Journal",
        readonly=False,
        # An explicit help is declared here, and not inherited from the company
        # field, so that this row of ir.model.fields carries its own translatable
        # term instead of an untranslated copy.
        help="Journal used for the reclassification entries of this company when "
             "neither the account of the bill line nor the journal of the bill "
             "defines a more specific one.",
    )
