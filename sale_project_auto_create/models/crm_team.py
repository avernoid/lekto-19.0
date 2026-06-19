# Part of Ganemo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class CrmTeam(models.Model):
    _inherit = "crm.team"

    auto_create_project = fields.Boolean(
        string="Create Project on Sales Confirmation",
        help="When enabled, confirming a sales order assigned to this sales team "
        "automatically creates a project linked to the order (with its analytic "
        "account), even if the order has no service product configured to generate "
        "one. This only sets the default for new orders; it can be overridden on "
        "each order.",
    )
