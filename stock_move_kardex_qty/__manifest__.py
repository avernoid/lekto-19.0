{
    "name": "Kardex Quantities & Value",
    "version": "19.0.4.0.0",
    "category": "Inventory/Reporting",
    "summary": "Signed quantity and signed value per stock movement (+in / -out "
               "/ 0) for a Kardex ledger, in the product's UoM / company currency.",
    "description": """
Kardex Quantities & Value
=========================

Adds two stored ledger columns on ``stock.move``:

* ``kardex_qty`` -- the valued **quantity** of the movement, signed as
  **+incoming / -outgoing** and **0** for anything that is neither (internal
  transfers, dropship, non-done moves), expressed in the product's reference UoM.
* ``kardex_value`` -- the native ``value`` **signed the same way**. Odoo stores
  ``value`` unsigned (its direction lives in the accounting entry's debit/credit,
  not in the number); this exposes that direction as a sign so the valuation
  column totalises like a ledger. It re-derives no valuation -- it only signs the
  already-stored ``value`` -- so it self-heals on any manual value / revaluation
  and never touches the done / posting / EDI flows.

Both share their sign (same stored ``is_in`` / ``is_out``).

``kardex_qty`` is the entry-level, **quantity-only** Kardex (stock ledger): the
quantity telescopes trivially -- Sum(in) - Sum(out) reconciles with the on-hand
valued quantity with no cost/valuation replay at all -- unlike a *valued* Kardex,
which must solve the cost-reconciliation problem.

The quantity is computed with ``_get_valued_qty()`` (the same base Odoo uses for
valuation, so consignment / non-picked lines are excluded) and is expressed in
the product's **reference Unit of Measure**. That UoM is exposed alongside as
``kardex_uom_id`` so a mixed-UoM subtotal is visibly meaningless instead of a
clean but wrong number.

The columns are injected as **optional columns into the native "Moves Analysis"
list** (Inventory > Reporting): ``kardex_qty`` and ``kardex_value`` shown by
default, ``kardex_uom_id`` hidden, all with green-in / red-out coloring and a
column footer total. No new view, menu, action, domain or group-by is added -- native
filtering and grouping are reused as-is. The inheritance also makes a few native
columns optional there: *Demand* (hidden by default), *Quantity*, *From* and *To*
(shown by default, now hideable). Generic: works on any localization.

Note: subtotals are meaningful only within a single product (or a
UoM-homogeneous group).
    """,
    "author": "Ganemo",
    "maintainer": "Ganemo",
    "company": "Ganemo",
    "website": "https://www.ganemo.co",
    "depends": ["stock_account"],
    "post_init_hook": "post_init_hook",
    "data": [
        "views/stock_move_kardex_views.xml",
    ],
    "demo": [
        "demo/kardex_qty_demo.xml",
    ],
    "icon": "/stock_move_kardex_qty/static/description/icon.png",
    "images": ["static/description/banner.png"],
    "license": "OPL-1",
    "installable": True,
    "auto_install": False,
    "application": False,
    "currency": "USD",
    "price": 44.0,
    "module_type": "official",
}
