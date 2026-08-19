{
    "name": "Stock Move Date Regularisation",
    "version": "19.0.1.2.3",
    "category": "Inventory/Inventory",
    "summary": "Regularise the date of stock movements whose source document does "
               "not expose an editable date.",
    "description": """
Stock Move Date Regularisation
==============================

In Odoo 19 valuation lives on ``stock.move`` and the Kardex / stock ledger reports
read ``stock.move.date``. Transfers let you correct that date -- unlock the transfer,
change ``date_done`` and Odoo propagates it to the movements. **No other source
does.** Scraps, inventory adjustments, manufacturing orders and disassemblies date
their movements at processing time with no way back.

This module adds a single guided wizard that regularises those dates, reachable from
the **Actions** menu of every relevant document and of the movements list itself.

What it does
------------

* **One wizard, every origin.** Resolves the selected records to their movements,
  shows exactly what will change grouped by origin, and applies it.
* **Two modes.** *Fixed date* sets everything to one instant; *Shift* moves the whole
  batch by an offset, preserving the intra-day spacing that was already correct.
* **Staggering.** Within one document, movements are separated by phase so a
  consumption never lands at the same second as the output it feeds.
* **Non-blocking warnings.** Flags movements that would end up before their own origin
  movements -- the silent way a FIFO chain gets broken.
* **No silent side effects.** Odoo cascades a document's date onto all of its movements,
  so selecting one line of a transfer moves them all. Those siblings are added to the
  selection, listed in the preview and traced like everything else, instead of moving
  unannounced. Untick the document sync to touch only what you picked.
* **Permanent trace.** ``original_date`` (written only once) and ``date_adjusted``
  on the movement, plus a chatter note on the source document with the reason.
* **Hard limits.** Future dates, a per-company maximum shift, and -- the one that
  matters -- movements cannot be dated into a closed accounting period.

What it does NOT do
-------------------

It does **not** revalue anything. The ``value`` of a done movement stays exactly as it
was computed at processing time. Note that re-dating *does* reorder the FIFO stack,
which is queried by date: it changes which layers stay open and what future outgoing
movements will cost.

By default it also leaves the valuation journal entry where it is. Moving it is an
explicit, off-by-default option: Odoo treats the date of a posted entry as unmodifiable,
so the option resets the entry to draft, clears its number, writes the new date and posts
it again. The entry is renumbered into the target period and leaves a sequence gap in the
original one. Entries that are reconciled, hash-protected, not posted, or in a closed
period are refused before anything is written.

Manufacturing orders and disassemblies are covered by the companion bridge module
``stock_move_date_adjust_mrp``.
    """,
    "author": "Ganemo",
    "maintainer": "Ganemo",
    "company": "Ganemo",
    "website": "https://www.ganemo.co",
    "depends": ["stock"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "wizard/stock_move_date_adjust_wizard_views.xml",
        "views/stock_move_views.xml",
        "data/server_actions.xml",
    ],
    "icon": "/stock_move_date_adjust/static/description/icon.png",
    "images": ["static/description/banner.png"],
    "license": "OPL-1",
    "installable": True,
    "auto_install": False,
    "application": False,
    "currency": "USD",
    "price": 89.0,
    "module_type": "official",
}
