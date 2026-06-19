# Part of Ganemo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeliveryLeadWorkdays(TransactionCase):
    """The module converts a working-days lead time into the native calendar-day
    ``customer_lead`` of each storable line, skipping weekends and holidays.

    All cases use a Mon-Fri (UTC) calendar and an order dated Monday
    2026-06-01, so the expected numbers are hand-derived and deterministic.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        # A self-contained Mon-Fri working calendar in UTC so calendar dates
        # match the naive UTC order date with no timezone drift.
        cls.calendar = cls.env["resource.calendar"].create({
            "name": "Test Mon-Fri (UTC)",
            "tz": "UTC",
            "company_id": cls.company.id,
            "attendance_ids": [
                (0, 0, {
                    "name": "Day %s" % dow,
                    "dayofweek": str(dow),
                    "hour_from": 8.0,
                    "hour_to": 16.0,
                    "day_period": "morning",
                })
                for dow in range(5)  # Monday (0) .. Friday (4)
            ],
        })

        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )
        cls.warehouse.resource_calendar_id = cls.calendar

        cls.partner = cls.env["res.partner"].create({"name": "Lead Time Customer"})
        cls.storable = cls.env["product.product"].create({
            "name": "Storable Widget",
            "type": "consu",
            "is_storable": True,
            "sale_delay": 5.0,  # native default we expect to be overwritten
        })
        cls.service = cls.env["product.product"].create({
            "name": "Setup Service",
            "type": "service",
            "sale_delay": 3.0,  # must stay untouched (not a storable line)
        })

    def _new_order(self, products=("storable",), commitment_date=False):
        lines = []
        for key in products:
            product = getattr(self, key)
            lines.append((0, 0, {
                "product_id": product.id,
                "product_uom_qty": 1.0,
            }))
        order = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "warehouse_id": self.warehouse.id,
            "commitment_date": commitment_date,
            "order_line": lines,
        })
        # Pin the order date to a known Monday for deterministic counting.
        order.date_order = fields.Datetime.to_datetime("2026-06-01 09:00:00")
        return order

    def _storable_line(self, order):
        return order.order_line.filtered(lambda line: line.product_id == self.storable)

    def test_weekends_are_skipped(self):
        """7 working days from Monday -> Wed of the 2nd week = 9 calendar days."""
        order = self._new_order()
        order.delivery_lead_workdays = 7
        order.action_recompute_delivery_lead()
        self.assertEqual(self._storable_line(order).customer_lead, 9.0)

    def test_holiday_is_skipped(self):
        """A global holiday inside the span pushes 7 working days to 10 days."""
        self.env["resource.calendar.leaves"].create({
            "name": "Public Holiday",
            "calendar_id": False,  # global: applies to every calendar
            "resource_id": False,  # public, not resource-specific
            "date_from": "2026-06-04 00:00:00",  # Thursday
            "date_to": "2026-06-04 23:59:59",
        })
        order = self._new_order()
        order.delivery_lead_workdays = 7
        order.action_recompute_delivery_lead()
        self.assertEqual(self._storable_line(order).customer_lead, 10.0)

    def test_only_storable_lines_are_filled(self):
        """Service lines keep their own native lead time; only storable change."""
        order = self._new_order(products=("storable", "service"))
        order.delivery_lead_workdays = 7
        order.action_recompute_delivery_lead()
        service_line = order.order_line.filtered(
            lambda line: line.product_id == self.service
        )
        self.assertEqual(self._storable_line(order).customer_lead, 9.0)
        self.assertEqual(service_line.customer_lead, 3.0)

    def test_commitment_date_leaves_lines_untouched(self):
        """With a manual Delivery Date, the deadline is native: do not overwrite."""
        order = self._new_order(
            commitment_date=fields.Datetime.to_datetime("2026-06-20 09:00:00")
        )
        order.delivery_lead_workdays = 7
        order.action_recompute_delivery_lead()
        # Stays at the product's native sale_delay, not the computed 9.
        self.assertEqual(self._storable_line(order).customer_lead, 5.0)

    def test_zero_workdays_does_not_overwrite(self):
        """An empty/zero working-days value must not wipe native lead times."""
        order = self._new_order()
        order.delivery_lead_workdays = 0
        order.action_recompute_delivery_lead()
        self.assertEqual(self._storable_line(order).customer_lead, 5.0)

    def test_button_reapplies_to_lines_added_later(self):
        """The button forces the value onto lines created after it was typed."""
        order = self._new_order()
        order.delivery_lead_workdays = 7
        order.action_recompute_delivery_lead()
        self.assertEqual(self._storable_line(order).customer_lead, 9.0)

        # A line added afterwards starts from the product's native lead time.
        new_line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": self.storable.id,
            "product_uom_qty": 2.0,
        })
        self.assertEqual(new_line.customer_lead, 5.0)

        # The button must bring every storable line in line with the value.
        order.action_recompute_delivery_lead()
        self.assertEqual(new_line.customer_lead, 9.0)

    def test_default_from_warehouse(self):
        """The order proposes the warehouse's default working-days lead time."""
        self.warehouse.delivery_lead_workdays = 4
        order = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "warehouse_id": self.warehouse.id,
        })
        self.assertEqual(order.delivery_lead_workdays, 4)

    def test_empty_warehouse_calendar_uses_raw_value(self):
        """Empty warehouse calendar -> NO conversion, raw value written.

        Even when the COMPANY has a working calendar, an empty warehouse
        'Delivery Working Calendar' must mean "no calculation": the warehouse
        field is the explicit switch (we do not fall back to the company
        calendar). This guards the reported regression where 15 became 21.
        """
        self.company.resource_calendar_id = self.calendar  # company DOES have one
        self.warehouse.resource_calendar_id = False
        order = self._new_order()
        order.delivery_lead_workdays = 15
        order.action_recompute_delivery_lead()
        self.assertEqual(self._storable_line(order).customer_lead, 15.0)
