from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _is_dropship_shipment(self):
        """A dropship created from a purchase: the vendor ships straight to the recipient."""
        self.ensure_one()
        return self.picking_type_code == 'dropship' and bool(self.purchase_id)

    def _is_customer_shipment(self):
        """The goods leave for a customer (not components sent to a subcontractor or a vendor)."""
        self.ensure_one()
        return self.location_dest_id.usage == 'customer'

    def _get_shipping_destination_partner(self):
        """Who receives the parcel.

        In a native dropship ``partner_id`` is the vendor (purchase_stock._prepare_picking)
        and the delivery address is the purchase ``dest_address_id``.
        """
        self.ensure_one()
        if self._is_dropship_shipment() and self.purchase_id.dest_address_id:
            return self.purchase_id.dest_address_id
        return self.partner_id

    def _get_shipping_origin_partner(self):
        """Who hands the parcel to the carrier: the vendor of a dropship, else the warehouse."""
        self.ensure_one()
        if self._is_dropship_shipment():
            return self.purchase_id.partner_id
        return self.picking_type_id.warehouse_id.partner_id
