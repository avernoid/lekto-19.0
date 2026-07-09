# Part of Ganemo. See LICENSE file for full copyright and licensing details.

import math
from datetime import datetime, time, timedelta

from pytz import timezone, utc

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    delivery_lead_workdays = fields.Integer(
        string="Lead time (workdays)",
        compute="_compute_delivery_lead_workdays",
        store=True,
        readonly=False,
        precompute=True,
        help="Delivery lead time expressed in WORKING days. When set, it is "
        "translated into calendar days using the warehouse working calendar "
        "(weekends and holidays excluded) and written into each storable line's "
        "lead time, so Odoo keeps computing the delivery date natively. "
        "Ignored when a manual Delivery Date is set on the order.",
    )

    @api.depends("warehouse_id")
    def _compute_delivery_lead_workdays(self):
        """Default the working-days lead time from the order's warehouse."""
        for order in self:
            order.delivery_lead_workdays = order.warehouse_id.delivery_lead_workdays

    # === Conversion: working days -> calendar days ===========================

    def _get_delivery_calendar(self):
        """The warehouse 'Delivery Working Calendar' is the explicit switch.

        When it is empty, NO working-day conversion is performed: the order's
        working-days value is written to the lines as-is (plain calendar days).
        We deliberately do not fall back to the company calendar, so an empty
        warehouse field always means "no calculation".
        """
        self.ensure_one()
        return self.warehouse_id.resource_calendar_id

    def _workdays_to_calendar_days(self, workdays):
        """Translate ``workdays`` working days into a calendar-day lead time.

        ``N`` working days are counted from the day AFTER the order date, using
        the resolved working calendar with holidays taken into account (both the
        global time off and the calendar's own time off). The returned value is
        the number of calendar days between the order date and the resulting
        delivery date, rounded up.

        Falls back to the raw number (naive calendar days) when no calendar is
        configured or the calendar yields no working day (e.g. empty calendar).
        """
        self.ensure_one()
        workdays = int(workdays or 0)
        if workdays <= 0:
            return 0.0

        calendar = self._get_delivery_calendar()
        if not calendar:
            # No working calendar available: keep the native naive behaviour.
            return float(workdays)

        order_dt = self.date_order or fields.Datetime.now()
        tz = timezone(calendar.tz or "UTC")
        order_local = utc.localize(order_dt).astimezone(tz)
        # Anchor at the start of the day AFTER the order date so the order day
        # itself is not counted as a working day (delivery is N working days
        # later), and so the order's time of day cannot shift the count.
        anchor = tz.localize(
            datetime.combine(order_local.date() + timedelta(days=1), time.min)
        )

        # compute_leaves=True is what makes plan_days subtract holidays; without
        # it, only weekends (non-working weekdays) would be skipped.
        delivery_dt = calendar.plan_days(workdays, anchor, compute_leaves=True)
        if not delivery_dt:
            return float(workdays)

        delta_days = (delivery_dt.astimezone(tz).date() - order_local.date()).days
        return float(math.ceil(max(delta_days, 0)))

    # === Application to the order lines =======================================

    def _delivery_lead_target_lines(self):
        """Lines that receive the computed lead time: storable products only."""
        self.ensure_one()
        return self.order_line.filtered(
            lambda line: not line.display_type
            and not line.is_downpayment
            and line.product_id.type == "consu"
        )

    def _apply_delivery_lead_workdays(self):
        """Write the calendar-day lead time onto the eligible lines.

        Does nothing when no working-days value is set, or when the order has a
        manual Delivery Date (``commitment_date``) -- in that case the deadline
        is governed by that date natively, so overwriting the line lead time
        would be misleading.
        """
        for order in self:
            if not order.delivery_lead_workdays or order.commitment_date:
                continue
            lead = order._workdays_to_calendar_days(order.delivery_lead_workdays)
            for line in order._delivery_lead_target_lines():
                if line.customer_lead != lead:
                    line.customer_lead = lead

    @api.onchange("delivery_lead_workdays")
    def _onchange_delivery_lead_workdays(self):
        """Spread the value to the lines as soon as it is typed in the form."""
        self._apply_delivery_lead_workdays()

    def action_recompute_delivery_lead(self):
        """Force re-applying the working-days lead time to every line.

        Exposed as a button next to the field: handy when lines are added after
        the lead time was entered, since that does not re-trigger the onchange.
        """
        self._apply_delivery_lead_workdays()
        return True

    def _action_confirm(self):
        # Re-anchor on the real confirmation date (``action_confirm`` has just
        # set ``date_order`` to now), and do it BEFORE super() so sale_stock's
        # procurement reads the freshly computed line lead times.
        self._apply_delivery_lead_workdays()
        return super()._action_confirm()
