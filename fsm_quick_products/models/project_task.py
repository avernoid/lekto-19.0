# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields

class ProjectTask(models.Model):
    _inherit = 'project.task'

    show_fsm_products_button = fields.Boolean(
        string="Show FSM Products Button",
        default=True,
        help="Controls the visibility of the direct products button in FSM tasks. Can be configured with Odoo Studio."
    )
