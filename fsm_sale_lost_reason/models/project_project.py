from odoo import fields, models

class Project(models.Model):
    _inherit = "project.project"

    use_lost_reason = fields.Boolean(
        string="Use Lost Reason",
        help="If enabled, tasks in this project will require a lost reason when marked as done without a sale."
    )
