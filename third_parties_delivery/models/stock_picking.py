from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    customer_id = fields.Many2one(
        comodel_name='res.partner',
        string='New delivery address',
        help='Specific address for the physical delivery of goods. Used when the delivery location differs from the invoice partner address.'
    )
    deliver_to_third_parties = fields.Boolean(
        string='Deliver to third parties',
        help='Check this box to specify a different delivery address (Point of Arrival) for the Electronic Delivery Guide.'
    )
    third_parties = fields.Selection(
        [
            ('01', 'Supplier'),
            ('02', 'Buyer')
        ],
        string='Supplier/Buyer',
        help='Select the type of third party involved in the operation.'
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('partner_id', False) and not vals.get('customer_id', False):
                vals['customer_id'] = vals['partner_id']
        return super(StockPicking, self).create(vals_list)

    @api.onchange('deliver_to_third_parties')
    def onchange_deliver_to_third_parties(self):
        self.customer_id = self.partner_id

    @api.onchange('partner_id')
    def onchange_deliver_partner_id(self):
        if not self.deliver_to_third_parties:
            self.customer_id = self.partner_id
