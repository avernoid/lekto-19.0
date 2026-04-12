from odoo import fields, models


class SaasInstanceEnvVar(models.Model):
    _name = 'saas.instance.env.var'
    _description = 'SaaS Instance Environment Variable'

    instance_id = fields.Many2one('saas.instance', required=True, ondelete='cascade')
    name = fields.Char(required=True)
    value = fields.Char()
    is_secret = fields.Boolean(default=True)
