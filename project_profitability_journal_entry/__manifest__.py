{
    "name": "Project Profitability - Journal Entries",
    "version": "19.0.1.0.1",
    "category": "Services/Project",
    "summary": """Include costs and revenues posted through manual journal """
    """entries on the project's analytic account in the profitability panel.""",
    "description": """
Project Profitability - Journal Entries
=======================================

The project profitability panel only accounts for what reaches the project
through a recognised document: customer invoices, vendor bills / purchase
orders, and (when installed) timesheet analytic items. A cost posted with a
plain manual journal entry on the project's analytic account is shown in the
Analytic Items list but never reaches the project margin.

This module adds those manual journal entries to the panel. On the project's
analytic account it reads the analytic items that come from a journal entry
(move type "Journal Entry") and adds them as dedicated cost / revenue
sections, so the margin reflects them too.

Self-contained and conflict-free
---------------------------------
* Works on its own, with no timesheet app installed (it only depends on
  Project and Accounting).
* It is purely additive: it calls super() and appends its own section, so it
  keeps working unchanged if Project / Sales / Timesheet layers are added on
  top.
* No double counting by construction. Its source is restricted to analytic
  items linked to a posted *journal entry* (``move_type = 'entry'``). That set
  is disjoint from the native sources: customer invoices (sale moves), vendor
  bills (purchase moves) and timesheets (analytic items with no journal item),
  so nothing is ever counted twice.
""",
    "author": "Ganemo",
    "maintainer": "Ganemo",
    "company": "Ganemo",
    "website": "https://www.ganemo.co",
    "depends": [
        "project",
        "account",
    ],
    "data": [],
    "icon": "/project_profitability_journal_entry/static/description/icon.png",
    "images": ["static/description/banner.png"],
    "license": "OPL-1",
    "installable": True,
    "auto_install": False,
    "application": False,
    "currency": "USD",
    "price": 90.0,
    "module_type": "official",
}
