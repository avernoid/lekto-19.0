{
    "name": "Account Reclassification for Manufacturing",
    "version": "19.0.2.0.0",
    "category": "Accounting/Accounting",
    "summary": """Split the counterpart of the native manufacturing entry by cost
        origin (materials, consumables, operations) and let each origin book to its
        own account.""",
    "description": """
Account Reclassification for Manufacturing
==========================================

Bridge between ``account_reclassification`` and ``mrp_account``. Installed
automatically when both are present, so a company that only needs the purchase
reclassification is never forced to install Manufacturing.

The problem
-----------

The entry that recognises a manufactured product credits **one single account**
for everything that went into it, and two facts of native Odoo make that credit
impossible to read:

* a **non-storable consumable** is valued into the finished product but generates
  no consumption entry of its own, so its cost is invisible;
* the **work centre operations** are always inside the value of the product,
  whether or not the labour entry is posted.

What this module does
---------------------

It opens that single credit line into one line per origin of the cost, each on
its own account::

    Debit   Stock                       89.10   <- unchanged
    Credit  Production account          60.00   <- materials + extra cost + rounding
    Credit  Recognition account          0.10   <- the consumable, by product/category
    Credit  Operations account          29.00   <- the work centre operations

Nothing is created and no amount changes: same entry, same total, same debit,
same direction. Only the accounts of the credit change.

The expense is already recorded by nature (the bill of the consumable with its
cost centre, the payroll of the labour) and this credit is what neutralises it
when the product is capitalised. Splitting it lets you compare the expense of a
process against what it added to the cost, and read the difference as a standard
cost deviation.

Configuration, all optional
---------------------------

* **Production Recognition Account** on the product or its category: the account
  credited for a non-storable component.
* **Production Operations Account** on the product or its category: the account
  credited for the work centre operations.
* **No Accounting Entry** on the work centre: do not post the labour entry for
  its operations. Analytic entries are NOT affected.

Every account resolves as product -> category -> its ancestors -> native
production location account, the same chain as the base module.

Safety
------

The split is applied only when the composition of the cost can be **proved**
against the invariant Odoo itself applies in ``_cal_price()``. A standard-cost
product, a move outside a manufacturing order, an unexpected shape or any
exception falls back to the single counterpart line the base module produces.
Valuation, kardex and average cost are never touched.

See ``DISENO_account_reclassification_mrp.md`` for the full design.
    """,
    "author": "Ganemo",
    "maintainer": "Ganemo",
    "company": "Ganemo",
    "website": "https://www.ganemo.co",
    "depends": [
        "account_reclassification",
        "mrp_account",
    ],
    "data": [
        "views/product_views.xml",
        "views/mrp_workcenter_views.xml",
    ],
    "icon": "/account_reclassification_mrp/static/description/icon.png",
    "images": ["static/description/banner.png"],
    "license": "OPL-1",
    "installable": True,
    "auto_install": True,
    "application": False,
    "currency": "USD",
    "price": 99.0,
    "module_type": "official",
}
