import logging

from odoo import _, fields, models
from odoo.tools import format_amount, formatLang

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    carrier_purchase_cost = fields.Float(
        string='Carrier Cost', digits='Product Price', readonly=True, copy=False,
        help='What the carrier charges for this shipment, as returned when the shipment was created. '
             'The Shipping Cost of the transfer is the price for the customer, 0 when the shipping is free.')
    carrier_purchase_line_id = fields.Many2one(
        'purchase.order.line', string='Transport Purchase Line', readonly=True, copy=False,
        index='btree_not_null', help='Purchase line that pays the transport of this shipment.')
    carrier_purchase_id = fields.Many2one(
        related='carrier_purchase_line_id.order_id', string='Transport Purchase',
        help='Purchase that pays the transport of this shipment.')
    carrier_purchase_canceled = fields.Boolean(
        string='Transport Purchase Cancelled', readonly=True, copy=False,
        help='The transport purchase line of this shipment was set to 0 because the shipment was cancelled.')
    carrier_purchase_error = fields.Char(
        string='Transport Purchase Error', readonly=True, copy=False,
        help='Why the transport purchase line was created at 0 or could not be created.')
    carrier_purchase_enabled = fields.Boolean(related='company_id.carrier_purchase')
    carrier_purchase_partner_id = fields.Many2one(related='carrier_id.purchase_partner_id')

    def write(self, vals):
        res = super().write(vals)
        if 'carrier_tracking_ref' in vals and not self.env.context.get('carrier_purchase_keep_description'):
            # the tracking reference often arrives after the validation: keep the description up to date
            for picking in self.filtered(lambda p: p.carrier_purchase_line_id and not p.carrier_purchase_canceled):
                line = picking.sudo().carrier_purchase_line_id
                line.name = picking._get_carrier_purchase_description(line.order_id.partner_id)
        return res

    def _action_done(self):
        res = super()._action_done()
        self._create_carrier_purchase_lines()
        return res

    def cancel_shipment(self):
        res = super(StockPicking, self.with_context(carrier_purchase_keep_description=True)).cancel_shipment()
        self._cancel_carrier_purchase(_('Shipment cancelled at the carrier'))
        return res

    # ------------------------------------------------------------------ #
    # Creation                                                           #
    # ------------------------------------------------------------------ #

    def _needs_carrier_purchase(self):
        self.ensure_one()
        return (self.company_id.carrier_purchase and self.state == 'done'
                and bool(self.carrier_id.purchase_partner_id) and not self.carrier_purchase_line_id
                and self._is_customer_shipment())

    def _get_legacy_carrier_purchase_lines(self):
        """Purchase lines already created for the transport by the delivery product of the sale
        (Purchase Automatically): the shipment must not buy it twice."""
        self.ensure_one()
        delivery_lines = self.sudo().sale_id.order_line.filtered('is_delivery')
        return delivery_lines.purchase_line_ids.filtered(lambda line: line.state != 'cancel')

    def _create_carrier_purchase_lines(self):
        """Buy the transport of the validated shipments. Nothing here may block the validation."""
        for picking in self.filtered(lambda p: p._needs_carrier_purchase()):
            if picking._get_legacy_carrier_purchase_lines():
                picking.message_post(body=_(
                    'Transport purchase not created: the sale order already has one, created by its '
                    'delivery product.'))
                continue
            try:
                with self.env.cr.savepoint():
                    picking.sudo()._create_carrier_purchase_line()
            except Exception as error:  # noqa: BLE001 - the shipment is validated whatever happens here
                _logger.warning('Transport purchase of %s not created: %s', picking.name, error)
                message = str(error) or error.__class__.__name__
                picking.carrier_purchase_error = message[:250]
                picking.sudo().activity_schedule(
                    'mail.mail_activity_data_warning',
                    note=_('Create the transport purchase of this shipment by hand: %s', message),
                    user_id=picking.user_id.id or self.env.uid)

    def _create_carrier_purchase_line(self):
        self.ensure_one()
        carrier = self.carrier_id
        error = False
        try:
            with self.env.cr.savepoint():
                cost = carrier._get_carrier_purchase_cost(self)
        except Exception as cost_error:  # noqa: BLE001 - no cost is no reason to lose the line
            cost, error = 0.0, str(cost_error) or cost_error.__class__.__name__
        order = self._get_carrier_purchase_order()
        price = self.company_id.currency_id._convert(
            cost, order.currency_id, self.company_id, fields.Date.context_today(self))
        line = self.env['purchase.order.line'].create(
            self._prepare_carrier_purchase_line(order, carrier._get_purchase_product(), price))
        self.write({'carrier_purchase_line_id': line.id, 'carrier_purchase_error': error and error[:250]})
        if error:
            body = _('Transport line of %(shipment)s created at 0: its cost could not be obtained (%(error)s).',
                     shipment=self.name, error=error)
            self.message_post(body=body)
            order.message_post(body=body)
        return line

    def _get_carrier_purchase_period(self):
        """Key of the request for quotation that gathers this shipment."""
        grouping = self.company_id.carrier_purchase_grouping
        day = fields.Date.context_today(self, self.date_done or fields.Datetime.now())
        if grouping == 'month':
            return day.strftime('%Y-%m')
        if grouping == 'week':
            year, week, _weekday = day.isocalendar()
            return '%s-W%02d' % (year, week)
        if grouping == 'day':
            return day.isoformat()
        return self.name

    def _get_carrier_purchase_order(self):
        """The open request for quotation of the vendor for the period, or a new one."""
        self.ensure_one()
        company = self.company_id
        vendor = self.carrier_id.purchase_partner_id
        currency = vendor.with_company(company).property_purchase_currency_id or company.currency_id
        period = self._get_carrier_purchase_period()
        PurchaseOrder = self.env['purchase.order'].with_company(company)
        if company.carrier_purchase_grouping != 'shipment':
            order = PurchaseOrder.search([
                ('carrier_purchase_period', '=', period),
                ('partner_id', '=', vendor.id),
                ('company_id', '=', company.id),
                ('currency_id', '=', currency.id),
                ('state', 'in', ('draft', 'sent')),
            ], order='id desc', limit=1)
            if order:
                return order
        return PurchaseOrder.create({
            'partner_id': vendor.id,
            'company_id': company.id,
            'currency_id': currency.id,
            'carrier_purchase_period': period,
            'origin': _('Transport %s', period),
        })

    def _prepare_carrier_purchase_line(self, order, product, price):
        vals = {
            'order_id': order.id,
            'product_id': product.id,
            'name': self._get_carrier_purchase_description(order.partner_id),
            'product_qty': 1.0,
            'product_uom': product.uom_po_id.id,
            'price_unit': price,
            'date_planned': self.date_done or fields.Datetime.now(),
        }
        distribution = self.sale_id.order_line.filtered('is_delivery')[:1].analytic_distribution
        if distribution:
            vals['analytic_distribution'] = distribution
        return vals

    def _get_carrier_purchase_description(self, vendor=None):
        """Transfer, tracking reference, destination and weight: what is needed to check the
        line against the carrier bill. In the language of the vendor."""
        self.ensure_one()
        picking = self.with_context(lang=(vendor and vendor.lang) or self.env.lang)
        destination = picking._get_shipping_destination_partner()
        lines = ['%s - %s' % (picking.carrier_id.name, picking.name)]
        if picking.carrier_tracking_ref:
            lines.append(picking.env._('Tracking: %s', picking.carrier_tracking_ref))
        details = []
        place = ' '.join(filter(None, [destination.zip, destination.city]))
        place = ', '.join(filter(None, [place, destination.country_id.code]))
        if place:
            details.append(picking.env._('To: %s', place))
        weight = picking.shipping_weight or picking.weight
        if weight:
            details.append('%s %s' % (formatLang(picking.env, weight), picking.weight_uom_name))
        if picking.sale_id:
            details.append(picking.sale_id.name)
        if details:
            lines.append(' · '.join(details))
        return '\n'.join(lines)

    # ------------------------------------------------------------------ #
    # Cancellation                                                       #
    # ------------------------------------------------------------------ #

    def _cancel_carrier_purchase(self, reason=False):
        """Never deletes the line: its price goes to 0 and its description says CANCELLED.
        A line already billed is left as it is (the vendor must issue a credit note)."""
        for picking in self.filtered(lambda p: p.carrier_purchase_line_id and not p.carrier_purchase_canceled):
            line = picking.sudo().carrier_purchase_line_id
            order = line.order_id
            env = picking.with_context(lang=order.partner_id.lang or self.env.lang).env
            if line.qty_invoiced:
                body = env._('The transport line of %(shipment)s in %(purchase)s is already billed and was not '
                             'changed: ask the vendor for a credit note.', shipment=picking.name, purchase=order.name)
                picking.message_post(body=body)
                order.message_post(body=body)
                continue
            old_price = format_amount(self.env, line.price_unit, order.currency_id)
            header = env._('CANCELLED')
            if reason:
                header = '%s: %s' % (header, reason)
            line.write({'price_unit': 0.0, 'name': '%s\n%s' % (header, line.name)})
            picking.carrier_purchase_canceled = True
            body = env._('Transport line of %(shipment)s cancelled (it was %(price)s).',
                         shipment=picking.name, price=old_price)
            if reason:
                body = '%s %s' % (body, reason)
            picking.message_post(body=body)
            order.message_post(body=body)

    # ------------------------------------------------------------------ #
    # Actions                                                            #
    # ------------------------------------------------------------------ #

    def action_create_carrier_purchase(self):
        """Button: buy the transport of a shipment validated before the option was enabled, or
        whose purchase failed. Errors are shown to the user."""
        for picking in self.filtered(lambda p: p._needs_carrier_purchase()):
            picking.sudo()._create_carrier_purchase_line()
        return True

    def action_view_carrier_purchase(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': self.carrier_purchase_id.id,
            'view_mode': 'form',
        }

    def action_cancel_carrier_purchase(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cancel Transport Purchase'),
            'res_model': 'carrier.purchase.cancel',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_picking_ids': self.ids},
        }
