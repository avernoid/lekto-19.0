from odoo import fields, models

class SaleLostReason(models.Model):
    _name = 'sale.lost.reason'
    _description = 'Sale Lost Reason'

    name = fields.Char('Name', required=True, translate=True)
    active = fields.Boolean('Active', default=True)
