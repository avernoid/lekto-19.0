from odoo import fields, models


class SaasProductOperationParam(models.Model):
    _name = 'saas.product.operation.param'
    _description = 'SaaS Product Operation Parameter'
    _order = 'operation_id, sequence, name'

    operation_id = fields.Many2one(
        'saas.product.operation', required=True, ondelete='cascade',
    )
    name = fields.Char(
        required=True,
        help="Parameter name used in the API payload (e.g. 'target_version').",
    )
    label = fields.Char(required=True)
    type = fields.Selection([
        ('char', 'String'),
        ('integer', 'Integer'),
        ('boolean', 'Boolean'),
        ('selection', 'Selection'),
    ], required=True, default='char')
    required = fields.Boolean(default=True)
    default_value = fields.Char(
        help="Default value serialized as string, parsed according to type.",
    )
    options = fields.Text(
        help="JSON array of {value, label} entries. Only used when type='selection'.",
    )
    sequence = fields.Integer(default=10)
