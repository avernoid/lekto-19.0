{
    "name": "Sale Delivery Lead Time in Working Days",
    "version": "19.0.1.0.2",
    "category": "Sales/Sales",
    "summary": """Enter the delivery lead time as working days (skipping """
    """weekends and holidays) and let it fill the native per-line lead time.""",
    "description": """
Sale Delivery Lead Time in Working Days
=======================================

Natively, Odoo computes the estimated delivery date as a plain calendar-day
offset: ``date_order + customer_lead`` (a ``timedelta`` in days). It never
accounts for weekends or public holidays. So a "7 working days" promise typed
as ``7`` actually lands on the 7th *calendar* day.

This module does **not** change any native calculation. Instead it adds a new
order-level field where you enter the lead time **in working days**. From that
number it computes the equivalent **calendar days** using a working calendar
(``resource.calendar``) -- skipping non-working days and holidays -- and writes
that calendar-day value into the native ``customer_lead`` of each storable
order line. Odoo then keeps computing everything exactly as before.

How the conversion works
------------------------

- The working calendar is the order's **warehouse** calendar
  (``resource_calendar_id``). It is the explicit switch: when the warehouse has
  no calendar, no conversion is done and the value is written to the lines as-is
  (plain calendar days).
- Holidays are taken from ``resource.calendar.leaves``: both the **global**
  leaves (not tied to any calendar) and the leaves of the **selected** calendar.
- ``N`` working days are counted **from the day after** the order date, and the
  resulting calendar-day span is written to ``customer_lead`` (rounded up).
  Example: ordering on a Monday with a Mon-Fri calendar, ``7`` working days
  resolve to ``9`` calendar days (one weekend in between); add a holiday in the
  span and it becomes ``10``.

Behaviour
---------

- A small **Recalculate** button next to the field re-applies the value to all
  lines (useful when you add a line after typing the lead time).
- If the order has a manual **Delivery Date** (``commitment_date``), that date
  governs the deadline natively, so this module leaves the lines untouched.
- The lead time is **re-anchored on confirmation** to the real confirmation
  date, so the working-day count always matches the actual order date.
- Only storable (``consu``) lines are filled; services, sections, notes and
  down payments are skipped.
""",
    "author": "Ganemo",
    "maintainer": "Ganemo",
    "company": "Ganemo",
    "website": "https://www.ganemo.co",
    "depends": [
        "sale_stock",
        "resource",
    ],
    "data": [
        "views/stock_warehouse_views.xml",
        "views/sale_order_views.xml",
    ],
    "icon": "/sale_delivery_lead_workdays/static/description/icon.png",
    "images": ["static/description/banner.png"],
    "license": "OPL-1",
    "installable": True,
    "auto_install": False,
    "application": False,
    "currency": "USD",
    "price": 71.0,
    "module_type": "official",
}
