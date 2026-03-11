# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProjectProject(models.Model):
    _inherit = 'project.project'

    require_start_to_sell = fields.Boolean(
        string="Require Start to Sell",
        default=False,
        help="If enabled, technicians must start the task timer (Start button) "
             "before they can add products or materials to this task.",
    )
