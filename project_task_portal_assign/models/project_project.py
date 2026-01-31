from odoo import fields, models

class Project(models.Model):
    _inherit = 'project.project'

    allow_portal_user = fields.Boolean(
        string='Allow Portal User Assignment',
        default=True,
        help="If checked, you can assign Portal Users to tasks in this project."
    )
