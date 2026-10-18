from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    carrier_purchase = fields.Boolean(
        string='Purchase Transport per Shipment',
        help='When a shipment to a customer is validated, add a purchase line for its transport for '
             'the vendor set on the shipping method.')
    carrier_purchase_grouping = fields.Selection([
        ('month', 'One request for quotation per vendor and month'),
        ('week', 'One request for quotation per vendor and week'),
        ('day', 'One request for quotation per vendor and day'),
        ('shipment', 'One purchase order per shipment'),
    ], string='Group Transport Purchases', default='month', required=True,
        help='Where the transport lines go. Grouped: one line per shipment in the open request for '
             'quotation of the vendor for the period; once it is confirmed, the next shipments go '
             'to a new one.')
