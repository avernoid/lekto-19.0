**Sale Delivery Lead Time in Working Days**

<img src="static/description/banner.png" width="100%" alt="Banner">

**Author**: [Ganemo](https://www.ganemo.com)

Enter the delivery lead time **in working days** on a sales order and let the
module translate it into the calendar-day value Odoo expects — skipping
weekends and holidays — without touching any native calculation.

## Why

Natively Odoo computes the estimated delivery date as a plain calendar-day
offset (`date_order + customer_lead`, a `timedelta` in days). It never accounts
for weekends or public holidays. So "7 working days" typed as `7` actually
lands on the 7th *calendar* day.

This module keeps the native engine untouched. It only computes the right
number *before* writing it into the native per-line lead time.

## How it works

- A new order field, **Lead time (workdays)**, holds your input.
- The working calendar is taken from the order's **warehouse**
  (`resource_calendar_id`). If that field is **empty, no conversion is done**
  and the value is written to the lines as plain days (simple mode).
- `N` working days are counted **from the day after** the order date using
  `resource.calendar.plan_days(..., compute_leaves=True)`. Holidays come from
  `resource.calendar.leaves`: both the **global** ones (no calendar assigned)
  and those of the **selected** calendar.
- The resulting calendar-day span is written (rounded up) into each storable
  line's native `customer_lead`. Odoo then keeps computing the delivery date,
  the stock move deadline and the picking schedule exactly as before.

### Example

Ordering on a Monday with a Mon–Fri calendar:

| Working days | Holidays in span | Calendar days written |
|---|---|---|
| 7 | none | 9 |
| 7 | 1 (e.g. Thursday) | 10 |

## Behaviour notes

- A small **Recalculate** button next to the field re-applies the value to all
  lines — useful when you add a line after typing the lead time (which does not
  re-trigger the onchange).
- If the order has a manual **Delivery Date** (`commitment_date`), that date
  governs the deadline natively, so the module leaves the lines untouched.
- The value is **re-anchored on confirmation** to the real confirmation date,
  so the working-day count always matches the actual order date.
- Only storable (`consu`) lines are filled; services, sections, notes and down
  payments are skipped.
- When the order's warehouse has no working calendar, it falls back to the
  native naive behaviour (calendar days = working days).

## Configuration

On each **Warehouse**:

- **Delivery Working Calendar** — the `resource.calendar` to use.
- **Default lead time (workdays)** — pre-fills new orders.

Public holidays are managed as **global time off** (Inventory/Resource
configuration) or as time off on the selected calendar.

## Technical

- Depends on `sale_stock` and `resource`.
- Adds no new stored business data beyond the warehouse defaults and the order
  input field; the actual scheduling stays in native `customer_lead`.

## License

OPL-1.
