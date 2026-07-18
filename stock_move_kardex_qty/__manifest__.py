{
    "name": "Kardex Quantities",
    "version": "19.0.1.0.1",
    "category": "Inventory/Reporting",
    "summary": "Signed valued quantity per stock movement (+in / -out / 0) for a "
               "quantity-only Kardex, in the product's reference UoM.",
    "description": """
Kardex Quantities
=================

Adds a single stored column ``kardex_qty`` on ``stock.move``: the valued
quantity of the movement, signed as **+incoming / -outgoing** and **0** for
anything that is neither (internal transfers, dropship, non-done moves).

It is the entry-level, **quantity-only** Kardex (stock ledger): the quantity
telescopes trivially -- Sum(in) - Sum(out) reconciles with the on-hand valued
quantity with no cost/valuation replay at all -- unlike a *valued* Kardex, which
must solve the cost-reconciliation problem.

The quantity is computed with ``_get_valued_qty()`` (the same base Odoo uses for
valuation, so consignment / non-picked lines are excluded) and is expressed in
the product's **reference Unit of Measure**. That UoM is exposed alongside as
``kardex_uom_id`` so a mixed-UoM subtotal is visibly meaningless instead of a
clean but wrong number.

Both fields are injected as **optional columns into the native "Moves Analysis"
list** (Inventory > Reporting): ``kardex_qty`` shown by default, ``kardex_uom_id``
hidden. No new view, menu, action, domain or group-by is added -- native
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
