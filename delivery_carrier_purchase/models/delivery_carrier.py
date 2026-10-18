from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    purchase_partner_id = fields.Many2one(
        'res.partner', string='Transport Vendor', check_company=True,
        help='Who is paid for the shipments of this method (the carrier, or the agency that '
             'bills it). Each validated shipment adds a purchase line for this vendor. Leave it '
             'empty to buy nothing.')
    purchase_product_id = fields.Many2one(
        'product.product', string='Transport Purchase Product', check_company=True,
        domain=[('type', '=', 'service')],
        help='Product of the purchase lines. Leave it empty to use the delivery product of the method.')
    purchase_cost_type = fields.Selection([
        ('shipment', 'Shipment cost'),
        ('fixed', 'Fixed cost'),
        ('vendor', 'Vendor price list'),
    ], string='Transport Cost', default='shipment', required=True,
        help='Shipment cost: what the carrier returns when the shipment is created (integrated '
             'carriers), or the price of the method computed with the real destination (fixed price '
             'and rule based methods).\n'
             'Fixed cost: the amount below for every shipment.\n'
             'Vendor price list: the vendor price of the purchase product.')
    purchase_fixed_cost = fields.Float(
        string='Transport Fixed Cost', digits='Product Price',
        help='Cost of every shipment, in the currency of the company.')
    carrier_purchase_enabled = fields.Boolean(compute='_compute_carrier_purchase_warning')
    purchase_auto_warning = fields.Boolean(
        compute='_compute_carrier_purchase_warning',
        help='The delivery product still creates a purchase by itself (Purchase Automatically).')

    @api.depends('product_id.service_to_purchase')
    @api.depends_context('company')
    def _compute_carrier_purchase_warning(self):
        enabled = self.env.company.carrier_purchase
        for carrier in self:
            carrier.carrier_purchase_enabled = enabled
            carrier.purchase_auto_warning = enabled and carrier.product_id.service_to_purchase

    def _keeps_shipment_cost(self):
        """Integrated carriers return what they charge when the shipment is created. Fixed price
        and rule based methods return the price for the customer: their cost is computed here."""
        return self.delivery_type not in ('fixed', 'base_on_rule')

    def _get_purchase_product(self):
        self.ensure_one()
        return self.purchase_product_id or self.product_id

    def send_shipping(self, pickings):
        res = super().send_shipping(pickings)
        if not self._keeps_shipment_cost():
            return res
        # keep what the carrier charges: the native shipping cost of the transfer is the price for
        # the customer, set to 0 when the shipping is free
        for picking, shipment in zip(pickings, res or []):
            if isinstance(shipment, dict) and shipment.get('exact_price'):
                picking.carrier_purchase_cost = shipment['exact_price']
        return res

    def _get_carrier_purchase_cost(self, picking):
        """Cost of the transport of a shipment, in the currency of its company."""
        self.ensure_one()
        company = picking.company_id
        today = fields.Date.context_today(self)
        if self.purchase_cost_type == 'fixed':
            return self.purchase_fixed_cost
        if self.purchase_cost_type == 'vendor':
            product = self._get_purchase_product()
            seller = product.with_company(company)._select_seller(
                partner_id=self.purchase_partner_id, quantity=1, date=today, uom_id=product.uom_po_id)
            if not seller:
                raise UserError(_('The vendor %(vendor)s has no price for %(product)s.',
                                  vendor=self.purchase_partner_id.display_name, product=product.display_name))
            return seller.currency_id._convert(seller.price, company.currency_id, company, today)
        if self._keeps_shipment_cost() and picking.carrier_purchase_cost:
            return picking.carrier_purchase_cost
        if self.delivery_type == 'fixed':
            return self.fixed_price
        if self.delivery_type == 'base_on_rule':
            return self._get_carrier_purchase_rule_price(picking)
        rate_method = '%s_rate_shipment' % self.delivery_type
        if picking.sale_id and hasattr(self, rate_method):
            rate = getattr(self, rate_method)(picking.sale_id)
            if not rate.get('success'):
                raise UserError(rate.get('error_message') or _('The carrier did not return a price.'))
            return rate['price']
        raise UserError(_('The shipping method %s did not return the cost of the shipment.', self.name))

    def _get_carrier_purchase_rule_price(self, picking):
        """Price of the rules of the method for the real destination of the shipment (the
        recipient of a dropship, not the vendor)."""
        destination = picking._get_shipping_destination_partner()
        if not self._match_address(destination):
            raise UserError(_('The shipping method %(method)s does not deliver to %(partner)s.',
                              method=self.name, partner=destination.display_name))
        total = 0.0
        if picking.sale_id:
            total = self._compute_currency(
                picking.sale_id, picking.sale_id._compute_amount_total_without_delivery(), 'pricelist_to_company')
        weight = picking.shipping_weight or picking.weight
        volume = sum(move.product_qty * move.product_id.volume for move in picking.move_ids)
        quantity = sum(picking.move_ids.mapped('product_qty'))
        return self._get_price_from_picking(total, weight, volume, quantity)
