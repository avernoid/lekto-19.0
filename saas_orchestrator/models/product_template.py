from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    saas_blueprint_id = fields.Many2one('saas.product.blueprint')
    saas_plan_id = fields.Many2one('saas.product.plan')
    is_saas_addon = fields.Boolean()
    addon_type = fields.Selection([
        ('env_vars', 'Extra Environment Variables'),
        ('storage_gb', 'Extra Storage GB'),
    ])
    addon_qty = fields.Integer()
