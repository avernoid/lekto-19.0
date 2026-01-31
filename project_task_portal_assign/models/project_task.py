from odoo import fields, models

class Task(models.Model):
    _inherit = 'project.task'

    allow_portal_user = fields.Boolean(
        related='project_id.allow_portal_user',
        readonly=True,
        string='Allow Portal User'
    )
