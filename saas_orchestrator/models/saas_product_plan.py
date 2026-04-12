from odoo import fields, models


class SaasProductPlan(models.Model):
    _name = 'saas.product.plan'
    _description = 'SaaS Product Plan'

    name = fields.Char(required=True)
    blueprint_id = fields.Many2one('saas.product.blueprint', required=True, ondelete='cascade')
    instance_type = fields.Char(default='t4g.small')
    deployment_mode = fields.Selection([
        ('dedicated', 'Dedicated'),
        ('shared', 'Shared'),
    ], default='dedicated', required=True)
    backup_retention_days = fields.Integer(default=7)
    history_max_records = fields.Integer(default=0, help="0 = unlimited")
    history_retention_days = fields.Integer(default=0, help="0 = unlimited")
    env_vars_included = fields.Integer(default=5)
    env_var_extra_price = fields.Float()
    storage_gb_included = fields.Integer(default=10)
    storage_gb_extra_price = fields.Float()
    product_template_id = fields.Many2one('product.template')
