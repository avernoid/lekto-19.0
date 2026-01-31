from odoo import models, fields

class DeliveryQuickReply(models.Model):
    _name = 'delivery.quick.reply'
    _description = 'Delivery Quick Reply'
    _order = 'sequence, name'

    name = fields.Char(string='Message', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)
