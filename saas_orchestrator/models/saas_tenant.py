from odoo import api, fields, models

from .utils import sanitize_slug


class SaasTenant(models.Model):
    _name = 'saas.tenant'
    _description = 'SaaS Tenant'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, tracking=True)
    slug = fields.Char(
        required=True, index=True, copy=False,
        help="Slug used as tenant_id in the orchestrator API",
    )
    partner_id = fields.Many2one('res.partner', required=True, tracking=True)
    instance_ids = fields.One2many('saas.instance', 'tenant_id')
    active = fields.Boolean(default=True)

    _slug_unique = models.Constraint(
        'UNIQUE(slug)',
        'Tenant slug must be unique.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('slug'):
                vals['slug'] = sanitize_slug(vals.get('name', ''), fallback='tenant')
        return super().create(vals_list)
