{
    "name": "Stock Move Date Regularisation - Manufacturing",
    "version": "19.0.1.2.3",
    "category": "Inventory/Inventory",
    "summary": "Extends movement date regularisation to manufacturing orders, "
               "by-products and disassemblies.",
    "description": """
Stock Move Date Regularisation - Manufacturing
==============================================

Bridge module. Adds manufacturing to ``stock_move_date_adjust``:

* **Manufacturing orders** -- components (``move_raw_ids``), finished product and
  by-products (``move_finished_ids``), in a single pass. The order's own
  ``date_start`` / ``date_finished`` are kept in sync, which on a done order requires
  the ``force_date`` context the core reserves for its work-order planner.
* **Disassemblies** -- both the consumption of the finished product and the return of
  the components. The order carries no date field of its own, so nothing is synced:
  its only date is ``create_date``, an ORM audit field that must not be falsified.

Components are staggered one hour before the finished product, so a consumption never
lands at the very same second as the output it feeds.
    """,
    "author": "Ganemo",
    "maintainer": "Ganemo",
    "company": "Ganemo",
    "website": "https://www.ganemo.co",
    "depends": ["stock_move_date_adjust", "mrp"],
    "data": [
        "data/server_actions.xml",
    ],
    "icon": "/stock_move_date_adjust_mrp/static/description/icon.png",
    "images": ["static/description/banner.png"],
    "license": "OPL-1",
    "installable": True,
    "auto_install": True,
    "application": False,
    "currency": "USD",
    "price": 49.0,
    "module_type": "official",
}
