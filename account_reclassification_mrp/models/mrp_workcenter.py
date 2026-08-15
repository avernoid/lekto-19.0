from odoo import fields, models


class MrpWorkcenter(models.Model):
    _inherit = "mrp.workcenter"

    reclass_skip_labour_entry = fields.Boolean(
        string="No Accounting Entry",
        help="Do not post the labour journal entry for the operations of this work "
             "centre.\n\n"
             "Use it when the cost of the work centre is already recognised through "
             "the entry of the manufactured product: posting the labour entry as well "
             "would credit the recognition accounts twice and leave a balance in the "
             "production location account.\n\n"
             "Analytic entries are NOT affected: they are created when the duration of "
             "the work order is set, independently of this setting, so the analytic "
             "distribution of the work centre keeps working as in native Odoo.\n\n"
             "When you tick this, point the 'Production Operations Account' of the "
             "manufactured product (or of its category) at a recognition account: "
             "leaving it on the production location account would produce a credit "
             "with no counterpart.",
    )
