# **Stock Value Variance — Kardex Columns**

<img src="static/description/banner.png" width="100%" alt="Banner">

A bridge with a single job: make the movement-level Kardex columns state what each movement is **really** worth once a late landed cost or vendor bill has been recorded against it.

It installs itself when both sides are present, and there is **nothing to configure**.

---

## Why it exists as a separate module

Two modules that must not depend on each other:

| Module | Owns | Depends on |
|---|---|---|
| [`stock_move_kardex_qty`](../stock_move_kardex_qty) | The Kardex columns on `stock.move` | `stock_account` **only** |
| [`stock_landed_cost_variance`](../stock_landed_cost_variance) | The `stock.value.variance` model | `stock_landed_costs`, `purchase_stock` |

Making the columns depend on the variance model would force **Landed Costs** onto every install of a generic ledger column. So the columns call a hook that returns nothing by default, and this bridge — installed automatically when both sides are present — supplies the real source and, just as importantly, **declares the dependencies that keep the columns fresh**.

Without it, the Kardex columns behave exactly as they did before.

---

## What it changes in the columns

Since **Stock Value Variance 19.0.2** a late revaluation (landed cost, bill, credit note) is written into the stored value of the deliveries it affects, at the moment it happens. The Kardex columns therefore read the corrected value directly, and this bridge only adds what no movement value can carry.

| Column | With the bridge |
|---|---|
| **Kardex Value** | The signed value of the movement plus any amount carried on top of it. |
| **Kardex Adjustment** | The amount carried on top: the value Odoo's average replay drops when goods arrive on negative stock, shown on the entry where it happens. Zero for every other movement. |

With the bridge, the sum of *Kardex Value* for a product equals the inventory value Odoo computes for it.

### The rule that makes the numbers safe

**Folded rows contribute zero.** Amounts already written into the stored value are flagged *Folded into Value* and are never added again. Correcting the same money twice is the classic failure of this kind of column, and it is ruled out by construction.

---

## Configuration

None.

1. Install **Kardex Quantities & Value**.
2. Install **Stock Value Variance**.
3. This module installs itself.
4. Show *Kardex Adjustment* from the optional-columns menu of the Moves Analysis list — it is hidden by default.

---

## What it does not do

* No new field, model, menu, action or view of its own — it inherits the existing list and adds one optional column.
* No stock move, no journal entry, no valuation rewritten. The accounting side belongs to `stock_landed_cost_variance`.
* No cron and no manual refresh: the columns are recomputed by the ORM the moment a variance changes.

---

## Technical notes

* The bridge overrides `_compute_kardex_variance` only to **re-declare `@api.depends`**. Odoo resolves a computed field's dependencies through the method it finds on the class, so overriding here extends them while `super()` keeps the base ones.
* It implements `_kardex_variance_amounts()`, the hook the base module calls; the base returns `(0.0, 0.0)` when no bridge is installed.
* The Kardex columns are **stored** computed fields. Any SQL write on `value`, `is_in`, `is_out` or `state` leaves them stale — this is true with or without the bridge. Recompute them through the ORM before committing.

---

**Author**: [Ganemo](https://www.ganemo.com)

**License**: OPL-1
