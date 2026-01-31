from odoo import models, fields

class ProjectQuickReply(models.Model):
    _name = 'project.quick.reply'
    _description = 'Project Task Quick Reply'
    _order = 'sequence, name'

    name = fields.Char(string='Message', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)
