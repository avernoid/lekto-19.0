from odoo import fields, models


class SaasProductBlueprint(models.Model):
    _name = 'saas.product.blueprint'
    _description = 'SaaS Product Blueprint'

    name = fields.Char(required=True)
    domain = fields.Char(help="Product domain managed in Cloudflare (e.g. orquestio.com)")
    cloudflare_zone_id = fields.Char()
    docker_image = fields.Char()
    terraform_module = fields.Char()
    container_port = fields.Integer()
    ports = fields.Char(help="Comma-separated ports to open (e.g. 3000,443)")
    access_url_template = fields.Char(help="e.g. https://{instance_id}.orquestio.com")
    health_check_endpoint = fields.Char(default="/api/health")
    requires_database = fields.Boolean()
    client_managed_config = fields.Boolean(default=True)
    plan_ids = fields.One2many('saas.product.plan', 'blueprint_id')
    active = fields.Boolean(default=True)
    operation_ids = fields.One2many('saas.product.operation', 'blueprint_id')
