import random

from odoo.addons.delivery_sendcloud.models.sendcloud_service import SendCloud


class _Overlay:
    """Read-only view of a record with some attributes replaced.

    The official connector reads the recipient from ``picking.partner_id`` and the sender
    from ``picking.picking_type_id.warehouse_id.partner_id`` (and, for rates, from
    ``picking.location_id.warehouse_id``). In a dropship those are the vendor and nothing.
    Handing the connector this view of the picking corrects them without writing on the
    transfer and without copying the connector code. Everything not overridden is read
    from the real record.
    """

    def __init__(self, record, **overrides):
        self.__dict__['_record'] = record
        self.__dict__['_overrides'] = overrides

    def __getattr__(self, name):
        overrides = self.__dict__['_overrides']
        if name in overrides:
            return overrides[name]
        return getattr(self.__dict__['_record'], name)

    def __setattr__(self, name, value):
        raise AttributeError('Read-only view of %s' % self.__dict__['_record'])


def _first(*values):
    return next((v for v in values if v), False)


def _contact_view(partner, *fallbacks):
    """The contact with email and phone completed from other contacts when it has none."""
    candidates = [partner, partner.commercial_partner_id]
    for fallback in fallbacks:
        if fallback:
            candidates += [fallback, fallback.commercial_partner_id]
    overrides = {}
    if not partner.email:
        overrides['email'] = _first(*(c.email for c in candidates))
    if not partner.phone and not partner.mobile:
        overrides['phone'] = _first(*(c.phone or c.mobile for c in candidates))
    return _Overlay(partner, **overrides) if overrides else partner


class SendCloudDropship(SendCloud):

    def _shipment_view(self, picking):
        """The picking as the connector must see it for an outgoing (non-return) parcel."""
        if isinstance(picking, _Overlay):
            return picking
        order_partner = picking.sale_id.partner_id
        recipient = picking._get_shipping_destination_partner()
        overrides = {
            'partner_id': _contact_view(recipient, order_partner),
            'destination_country_code': recipient.country_id.code,
        }
        if picking._is_dropship_shipment():
            sender = _contact_view(picking._get_shipping_origin_partner(), picking.company_id.partner_id)
            warehouse = _Overlay(picking.picking_type_id.warehouse_id, partner_id=sender)
            overrides.update({
                'picking_type_id': _Overlay(picking.picking_type_id, warehouse_id=warehouse),
                'location_id': _Overlay(picking.location_id, warehouse_id=warehouse),
            })
        return _Overlay(picking, **overrides)

    def _send_shipment(self, picking, is_return=False):
        if not is_return:
            picking = self._shipment_view(picking)
        return super()._send_shipment(picking, is_return=is_return)

    def _get_pick_sender_address(self, picking):
        # Dropship: the sender is the vendor, sent as from_* fields (Sendcloud does not allow
        # 'sender_address' and from_* together). The option does the same for the warehouse.
        if picking._is_dropship_shipment() or picking.carrier_id.sendcloud_sender_from_odoo:
            return None
        return super()._get_pick_sender_address(picking)

    def _prepare_parcel(self, picking, sender_id, is_return):
        parcels = super()._prepare_parcel(picking, sender_id, is_return)
        contract = picking.carrier_id.sendcloud_contract_id
        if contract:
            for parcel in parcels:
                parcel['contract'] = contract
        return parcels

    def _get_shipping_rate(self, carrier, order=None, picking=None, parcel=None, order_weight=None):
        if picking and not order:
            picking = self._shipment_view(picking)
        return super()._get_shipping_rate(carrier, order=order, picking=picking, parcel=parcel,
                                          order_weight=order_weight)


# Shipping products offered by the simulated Sendcloud account ("Load your products").
SIMULATED_PRODUCTS = [
    ('ups:standard', 'ups', 'UPS Standard', 1, 70001),
    ('gls_es:business_parcel', 'gls_es', 'GLS Business Parcel', 1, 40001),
    ('correos_express:paq24', 'correos_express', 'Correos Express Paq 24', 1, 40001),
]
def _address_lines(name, company, street, street2, postal_code, city, country):
    lines = [name or company or '']
    if company and company != name:
        lines.append(company)
    lines += [street or '', street2 or '', ' '.join(filter(None, [postal_code, city])), country or '']
    return [line for line in lines if line]


def simulated_label(parcel):
    """A 4x6 in shipping label drawn from the simulated parcel: carrier, sender, recipient,
    tracking number with its barcode, and a clear mark that it is not valid for shipping."""
    from io import BytesIO
    from reportlab.graphics.barcode import code128
    from reportlab.lib.colors import Color, black, white
    from reportlab.pdfgen import canvas

    width, height = 288, 432
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(width, height), pageCompression=0)
    pdf.setTitle('Simulated label %s' % parcel['tracking_number'])
    # carrier band
    pdf.setFillColor(black)
    pdf.rect(0, height - 46, width, 46, stroke=0, fill=1)
    pdf.setFillColor(white)
    pdf.setFont('Helvetica-Bold', 17)
    pdf.drawString(12, height - 30, (parcel['service'] or 'Sendcloud')[:28].upper())
    pdf.setFillColor(black)
    # sender
    y = height - 64
    pdf.setFont('Helvetica-Bold', 7)
    pdf.drawString(12, y, 'FROM')
    pdf.setFont('Helvetica', 8)
    for line in parcel['sender'][:5]:
        y -= 10
        pdf.drawString(12, y, line[:55])
    # recipient
    y -= 18
    pdf.line(12, y + 8, width - 12, y + 8)
    pdf.setFont('Helvetica-Bold', 8)
    pdf.drawString(12, y - 4, 'SHIP TO')
    pdf.setFont('Helvetica-Bold', 12)
    for line in parcel['recipient'][:6]:
        y -= 16
        pdf.drawString(12, y - 4, line[:36])
    # tracking number and barcode
    y -= 30
    pdf.line(12, y + 8, width - 12, y + 8)
    pdf.setFont('Helvetica', 8)
    pdf.drawString(12, y - 6, 'Order %s  -  Weight %s kg' % (parcel['order'] or '-', parcel['weight'] or '-'))
    barcode = code128.Code128(parcel['tracking_number'], barHeight=46, barWidth=1.1)
    barcode.drawOn(pdf, max(0, (width - barcode.width) / 2), y - 68)
    pdf.setFont('Helvetica-Bold', 12)
    pdf.drawCentredString(width / 2, y - 84, parcel['tracking_number'])
    # simulation mark
    pdf.setFillColor(Color(0.85, 0.1, 0.1))
    pdf.rect(0, 0, width, 30, stroke=0, fill=1)
    pdf.setFillColor(white)
    pdf.setFont('Helvetica-Bold', 10)
    pdf.drawCentredString(width / 2, 11, 'SIMULATION - NOT VALID FOR SHIPPING')
    pdf.saveState()
    pdf.setFillColor(Color(0.85, 0.1, 0.1, alpha=0.18))
    pdf.setFont('Helvetica-Bold', 44)
    pdf.translate(width / 2, height / 2)
    pdf.rotate(55)
    pdf.drawCentredString(0, 0, 'SIMULATION')
    pdf.restoreState()
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


class SendCloudSimulation(SendCloudDropship):
    """Answers like the Sendcloud API without any network call (demos and training).

    The whole connector runs (products, rates, parcel creation with label and tracking number,
    cancellation); the parcel statuses are simulated by the delivery state hook."""

    def __init__(self, public_key, private_key, logger, carrier):
        super().__init__(public_key, private_key, logger)
        self._carrier = carrier
        self._picking = None
        self._labels = {}

    def _send_shipment(self, picking, is_return=False):
        # keep the transfer: the label shows the warehouse address when the parcel only names
        # a Sendcloud sender address
        self._picking = picking
        return super()._send_shipment(picking, is_return=is_return)

    def _simulated_parcel_label(self, parcel, parcel_id, tracking_number):
        if parcel.get('from_name') or parcel.get('from_company_name'):
            sender = _address_lines(parcel.get('from_name'), parcel.get('from_company_name'),
                                    parcel.get('from_address_1'), parcel.get('from_address_2'),
                                    parcel.get('from_postal_code'), parcel.get('from_city'),
                                    parcel.get('from_country'))
        else:
            partner = self._picking.picking_type_id.warehouse_id.partner_id if self._picking else None
            sender = _address_lines(partner.name, False, partner.street, partner.street2, partner.zip,
                                    partner.city, partner.country_id.code) if partner else []
        product = self._carrier.sendcloud_shipping_id
        self._labels[str(parcel_id)] = {
            'service': product.name or self._carrier.name,
            'sender': sender,
            'recipient': _address_lines(parcel.get('name'), parcel.get('company_name'), parcel.get('address'),
                                        parcel.get('address_2'), parcel.get('postal_code'), parcel.get('city'),
                                        parcel.get('country')),
            'tracking_number': tracking_number,
            'order': parcel.get('order_number'),
            'weight': parcel.get('weight'),
        }

    def _get_pick_sender_address(self, picking):
        if picking._is_dropship_shipment() or picking.carrier_id.sendcloud_sender_from_odoo:
            return None
        return 1  # the simulated account has one sender address, whatever the warehouse name

    def _simulated_products(self, carrier_code=None):
        products = []
        for code, carrier, name, min_weight, max_weight in SIMULATED_PRODUCTS:
            if carrier_code and carrier != carrier_code:
                continue
            products.append({
                'code': code, 'carrier': carrier, 'name': name, 'service_points_carrier': carrier,
                'weight_range': {'min_weight': min_weight, 'max_weight': max_weight},
                'available_functionalities': {'last_mile': ['home_delivery'], 'multicollo': [True]},
                'methods': [{'id': 900000 + len(products) + 1, 'name': '%s (simulation)' % name,
                             'functionalities': {}, 'shipping_product_code': code,
                             'properties': {'min_weight': min_weight, 'max_weight': max_weight}}],
            })
        product = self._carrier.sendcloud_shipping_id
        if product and not any(p['code'] == product.sendcloud_code for p in products) \
                and (not carrier_code or carrier_code == product.carrier):
            products.append({
                'code': product.sendcloud_code, 'carrier': product.carrier, 'name': product.name,
                'service_points_carrier': product.carrier,
                'weight_range': {'min_weight': product.min_weight, 'max_weight': product.max_weight},
                'available_functionalities': {}, 'methods': [{
                    'id': 900099, 'name': '%s (simulation)' % product.name, 'functionalities': {},
                    'shipping_product_code': product.sendcloud_code,
                    'properties': {'min_weight': product.min_weight, 'max_weight': product.max_weight}}],
            })
        return products

    def _send_request(self, endpoint, method='get', data=None, params=None, route=None):
        self.logger('%s %s (simulated)' % (method, endpoint), 'sendcloud simulation')
        if endpoint == 'shipping-products':
            return self._simulated_products((params or {}).get('carrier'))
        if endpoint == 'shipping-functionalities':
            return {}
        if endpoint == 'shipping-price':
            return [{'price': '6.90', 'currency': 'EUR'}]
        if endpoint == 'user/addresses/sender':
            return {'sender_addresses': [{'id': 1, 'label': 'Simulation', 'contact_name': 'Simulation'}]}
        if endpoint == 'parcels' and method == 'post':
            prefix = self._carrier.delivery_simulation_prefix or ''
            parcels = []
            for parcel in data['parcels']:
                parcel_id = random.randint(100000000, 999999999)
                tracking_number = '%s%s' % (prefix, random.randint(1000000000, 9999999999))
                self._simulated_parcel_label(parcel, parcel_id, tracking_number)
                parcels.append({
                    'id': parcel_id, 'colli_uuid': 'simulation-%s' % parcel_id,
                    'tracking_number': tracking_number,
                    'tracking_url': False, 'weight': parcel.get('weight'), 'shipment': parcel.get('shipment'),
                    'documents': [{'link': 'simulation/label/%s' % parcel_id, 'type': 'label'}],
                })
            return {'parcels': parcels}
        if endpoint.startswith('parcels/') and endpoint.endswith('/cancel'):
            return {'status': 'cancelled', 'message': 'Parcel cancelled (simulation)'}
        if endpoint.startswith('parcels/'):
            return {'parcel': {'id': endpoint.split('/')[1], 'tracking_url': False,
                               'status': {'id': 1000, 'message': 'Ready to send'}}}
        return {}

    def _get_document(self, url):
        parcel_id = url.rstrip('/').rsplit('/', 1)[-1]
        label = self._labels.get(parcel_id) or {
            'service': self._carrier.name, 'sender': [], 'recipient': [], 'tracking_number': parcel_id,
            'order': False, 'weight': False}
        return simulated_label(label)
