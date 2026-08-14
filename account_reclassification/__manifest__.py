{
    "name": "Account Reclassification",
    "version": "19.0.6.0.0",
    "category": "Accounting/Accounting",
    "summary": """Post a parallel reclassification entry on vendor bills, and let the
        product category decide the counterpart account of the native production
        entry, without touching the inventory valuation.""",
    "description": """
Account Reclassification
========================

Many charts of accounts ask for the same economic fact to be shown against more
than one account. A purchase hits its destination account, but must also be
presented **by nature**; a component consumed in production must hit the account
of **its own family of products**, not one single account for the whole plant.

This module covers both, without ever touching the native valuation engine, the
stock ledger or the average cost.

Two independent blocks
----------------------

**1. Production / consumption account on the product category**

A ``reclass_production_account_id`` field on ``product.category`` (company
dependent, like the native valuation accounts) with recursive fallback to the
parent categories.

No extra entry and no extra move is ever created: the native
production/consumption entry of ``stock_account`` is kept as is, only the
counterpart account is resolved differently.

* Manufacturing only: moves in and out of a production location resolve the
  account as category -> parent -> grandparent -> ... and, when no ancestor
  defines one, the native ``location.valuation_account_id``.
* Because natively a location without an account means *no entry at all*, the
  category account is resolved before that decision is taken: a movement that
  would go unrecorded is booked against the category account instead. Every
  other native guard stays (non-storable, non-valued, zero quantity and
  periodic valuation still produce no entry).
* Everything else is left strictly native, including the native decision of
  booking nothing: receipts, deliveries, internal transfers, scrap and inventory
  adjustments.

**2. Reclassification entry on vendor bills**

When a vendor bill is posted, every product line whose account is set to be
reclassified produces a balanced pair of lines (target / counterpart) in a
dedicated journal entry. Design rules:

* Fail-safe: a line without configuration is skipped; the bill posts natively.
* Idempotent: regenerating always cancels/removes the previous entry first, so
  a bill can never end up with two active reclassifications. Available one by
  one on the bill and in bulk from the list view.
* Lock dates: every create/cancel is validated against the native fiscal year,
  purchase and hard lock dates.
* Company currency: amounts are taken from the line balance, already converted.
* Analytics: the analytic distribution of the source line is copied to *both*
  lines, so the reclassification is visible per analytic account while the
  analytic totals stay untouched (no double counting of the cost).

Typical use cases
-----------------

* Charts of accounts that present purchases by nature against a stock variation
  account (Peru PCGE 60/61, Spain grupo 6, France classe 6, and any plan
  following the same continental logic).
* Manufacturers that need the cost of consumed materials split by family of
  products instead of one single production account.
* Any company that must report the same operation under two account structures
  without duplicating documents or disturbing inventory valuation.

Nothing here depends on a localization module: it works on any chart of
accounts, and it is inert until you configure it.
    """,
    "author": "Ganemo",
    "maintainer": "Ganemo",
    "company": "Ganemo",
    "website": "https://www.ganemo.co",
    "depends": [
        "stock_account",
    ],
    "data": [
        "views/product_category_views.xml",
        "views/account_account_views.xml",
        "views/account_journal_views.xml",
        "views/account_move_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "icon": "/account_reclassification/static/description/icon.png",
    "images": ["static/description/banner.png"],
    "license": "OPL-1",
    "installable": True,
    "auto_install": False,
    "application": False,
    "currency": "USD",
    "price": 149.0,
    "module_type": "official",
}
