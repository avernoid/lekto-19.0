from odoo import fields, models


class SaasProductOperation(models.Model):
    _name = 'saas.product.operation'
    _description = 'SaaS Product Operation'
    _order = 'blueprint_id, sequence, code'

    blueprint_id = fields.Many2one(
        'saas.product.blueprint', required=True, ondelete='cascade',
    )
    code = fields.Char(
        required=True,
        help="Unique operation code within the blueprint (e.g. 'upgrade', 'restart').",
    )
    label = fields.Char(required=True)
    description = fields.Text()
    script_path = fields.Char(
        required=True,
        help="Path on the EC2 host to the script that implements this operation.",
    )
    requires_drain = fields.Boolean(
        default=False,
        help="If True, the dispatcher runs drain_command before invoking the script.",
    )
    drain_command = fields.Char(
        help="Shell command executed to drain the product's queue before the operation.",
    )
    timeout_seconds = fields.Integer(default=300)
    visible_in_admin = fields.Boolean(default=True)
    visible_in_portal = fields.Boolean(default=False)
    sequence = fields.Integer(default=10)
    param_ids = fields.One2many(
        'saas.product.operation.param', 'operation_id',
    )

    _code_unique_per_blueprint = models.Constraint(
        'UNIQUE(blueprint_id, code)',
        'Operation code must be unique within a blueprint.',
    )
