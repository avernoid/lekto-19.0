**Stock Move Date Regularisation - Manufacturing**

<img src="static/description/banner.png" width="100%" alt="Banner">

Bridge module. Extends **Stock Move Date Regularisation** to Manufacturing Orders,
by-products and Disassemblies.

---

## Why this module exists

Once a Manufacturing Order reaches state **Done**, Odoo refuses to move its dates. The
form makes *Start Date* read-only, *End Date* is not displayed at all, and the server
raises:

> You cannot move a manufacturing order once it is cancelled or done.

Its movements — the components consumed and the goods produced — are therefore frozen on
the day you validated, regardless of when the work actually happened. A Disassembly is
worse still: it carries **no date field at all**, and its movements inherit the moment
the draft record was created, not the moment it was validated.

This bridge makes both correctable through the same wizard as every other origin.

---

## What it adds

| Origin | Movements covered | Document header kept in sync |
|---|---|---|
| Manufacturing Order | Components (`move_raw_ids`) | *Start Date* = earliest component date |
| Manufacturing Order | Finished product and by-products (`move_finished_ids`) | *End Date* = latest output date |
| Disassembly | Consumption of the finished product **and** return of the components | None — see below |

It also adds the origin labels shown in the wizard preview — *Manufacturing -
Components*, *Manufacturing - Finished Product* and *Disassembly* — and the staggering
rule that puts consumption one hour before output.

---

## Installation

Nothing to do. This module is `auto_install`: it comes in on its own as soon as both
**Manufacturing** (`mrp`) and **Stock Move Date Regularisation**
(`stock_move_date_adjust`) are installed.

It adds no settings, no menus, no new views and no new fields. Permissions and limits
are inherited from the base module.

---

## User guide

Open a **Manufacturing Order** or a **Disassembly** — or select several from their
list — and use the **Actions** menu (the gear next to the record name). The wizard is
the one documented in the base module's README.

Two behaviours specific to manufacturing:

**Both sides travel together.** Selecting a Manufacturing Order resolves to its
components *and* its finished product *and* its by-products. Re-dating only one side
would leave a consumption in one month and its output in another, which is worse than
the problem you started with.

**Staggering is on by default.** Components land on the chosen instant, the finished
product one hour later. If everything landed on the same second, the ledger would lose
the intra-day sequence and the tie-break would fall to internal record IDs. For a
Disassembly the same rule applies: the consumption of the finished product first, the
return of the components an hour later.

---

## Frequently asked questions

**Is it safe to override the "done order" guard?**
Yes. The bridge uses the `force_date` context key — the exact mechanism the Odoo core
itself uses when its work-order planner needs to rewrite those same dates
(`mrp/models/mrp_production.py`). No core file is patched and no guard is removed.

**What happens to an order that is still open and planned?**
Native behaviour, deliberately. On an order that is not done or cancelled, the bridge
writes the dates normally, which lets Odoo unplan the work orders exactly as it does
when you edit the date by hand. The special path is reserved for orders already done or
cancelled, where unplanning makes no sense.

**Why is the Disassembly's date not updated?**
Because it has none. `mrp.unbuild` has no date field; the only date on the record is the
technical *Created on* stamp, which is an ORM audit field. Falsifying when a record was
created would be worse than the problem being fixed, so it is left alone. Since no
Disassembly view displays a date, nothing looks inconsistent to the user.

**A side effect worth checking in your data:** because Disassembly movements are dated
from the record's *creation*, an order created in one month and validated in the next
produces movements that were already mis-dated before anyone touched anything.

**Are work-order durations affected?**
No. Only `date_start` and `date_finished` on the order and the dates of its stock
movements are written.

**Does it revalue production costs?**
No. Like the base module, it never recomputes a stored movement value. It does affect
FIFO layer consumption going forward, because that stack is ordered by date.

---

## Technical notes

- `stock.move._date_adjust_origin()` is extended with `production_raw`,
  `production_finished` and `unbuild`. Manufacturing movements never carry a transfer,
  so testing them first cannot shadow the base classification.
- Disassemblies are resolved through **`unbuild_id`**. The Odoo core never populates
  `consume_unbuild_id` — both movement generators stamp `unbuild_id` on every movement,
  consumption included — so the field is only read defensively, in case a third party
  does populate it.
- `_date_adjust_sync_document()` writes `date_start` from the minimum of the component
  targets and `date_finished` from the maximum of the output targets, in a single write
  per order.

---

**Author**: [Ganemo](https://www.ganemo.com)

License: OPL-1. Compatible with Odoo 19 Enterprise, Odoo.SH and Ganemo Online. Not
supported on Odoo Online (custom code restrictions).
