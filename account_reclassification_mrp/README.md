# **Account Reclassification for Manufacturing**

<img src="static/description/banner.png" width="100%" alt="Banner">

The entry that recognises a manufactured product credits **one single account** for everything that went into it. This bridge **opens that credit by origin** — storable materials, non-storable consumables and work centre operations — each on its own account, **without creating a single extra line of accounting** and **without touching the native valuation**.

It extends [`account_reclassification`](../account_reclassification) with [`mrp_account`](https://www.odoo.com). It installs itself automatically when both are present, so a company that only needs the purchase reclassification is never forced to install Manufacturing. Like the base module, it depends on **no localization** and is **inert until you configure it**.

---

## The problem, in one entry

A manufacturing order with two storable components (60.00), one consumable (0.10) and one work centre operation (29.00) produces **three** native entries:

| Entry | Debit | Credit |
|---|---|---|
| Component consumption | Production location 60.00 | Stock 60.00 |
| Finished product | Stock 89.10 | Production location 89.10 |
| Labour (`_post_labour`) | Production location 29.00 | Work centre expense 29.00 |

Two facts of native Odoo make the cost hard to read:

* The **consumable is valued but never booked**. Odoo puts its 0.10 into the value of the finished product, yet it generates no consumption entry of its own — non-storable products are filtered out of the entry, not out of the valuation. Its cost is therefore **invisible** inside that single credit.
* The **operations are always inside the value** of the product, whether or not the labour entry is posted.

So the second entry credits 89.10 against one account, and there is no way to tell how much of it was material, how much was the consumable and how much was labour.

---

## What this module writes instead

```
Debit   Stock                       89.10   ← unchanged
Credit  Production account          60.00   ← materials + extra cost + rounding
Credit  Recognition account          0.10   ← the consumable, by product/category
Credit  Operations account          29.00   ← the work centre operations
```

Same entry, same total, same debit. Only the credit is opened.

**Why it is worth it.** The expense is already recorded **by nature** — the vendor bill of the consumable with its cost centre, the payroll of the labour. The credit of the recognition entry is what **neutralises** that expense when the product is capitalised. Splitting it lets you compare, account by account, *the expense of a process* against *what it added to the cost* — and read the difference as a **standard cost deviation**.

---

## Configuration

Everything is optional. With nothing configured the module is inert and the behaviour is strictly native.

| Where | Field | What it does |
|---|---|---|
| **Product / Product Category** | **Production Recognition Account** | Account credited for the cost of THIS product when it is consumed as a non-storable component. |
| **Product / Product Category** | **Production Operations Account** | Account credited for the cost of the work centre operations of the order. |
| **Work Centre** | **No Accounting Entry** | Do not post the labour entry for the operations of this work centre. |

### One resolution rule for every account

```
the product  →  its category  →  parent  →  grandparent  →  …  →  production location account
```

The first level that defines the account wins. This is the same chain as the **Production/Consumption Account** of the base module, so there is only one rule to learn.

### Keeping the two settings coherent

The labour entry **debits the production location account**. That is the only thing you have to keep in mind:

| Setup | Result |
|---|---|
| Operations account **empty** | The operations are credited on the production location account, where the labour entry clears them. Native balance. |
| Operations account **set** + labour entry **suppressed** on those work centres | The credit neutralises the payroll expense already booked by nature. Nothing is left in the location. |
| Operations account **set** + labour entry **still posted** | Its debit of 29.00 stays on the production location account. |

The module **obeys what you configure** and never guesses which of the two you meant — including when some work centres of the same order are flagged and others are not: **all** the operations go to the configured account. The help text of both fields says so, and the third row is a configuration decision, not a defect.

> **Alternative with no configuration at all**: emptying the valuation account of the production location makes Odoo skip the labour entry natively (its own guard), and the *rescue* of the base module still books the consumption and finished goods entries against the category accounts. Same result as the flag, but it is per location and all-or-nothing; the flag gives you granularity per work centre.

---

## How the split is built

| Origin | Amount | Account |
|---|---|---|
| **Consumables** | Σ `value` of the non-storable components, **grouped by the account each one resolves** | Production Recognition Account |
| **Operations** | Σ `_cal_cost()` of the work orders, rounded **per work order** exactly like `_post_labour` does | Production Operations Account |
| **Remainder** | value of the move − the above | Production/Consumption Account of the category (base module) |

* Two consumables resolving **different** accounts produce **two** lines; two resolving the same one are added together. A consumable that resolves none falls into the remainder, so its value is never lost.
* The remainder is taken **by difference, never by addition**. It absorbs the storable materials, the `extra_cost`, and every rounding cent — so the entry **always balances**.
* **Byproducts** with a cost share receive the same breakdown, prorated by their share of the batch, with their own product on their own lines.
* **Backorders** post one entry per batch: Odoo creates a new order per batch, so each entry contains only its own.

### The safety net

Before splitting anything, the module checks the invariant Odoo itself applies in `_cal_price()`:

```
Σ value(raw moves done) + Σ _cal_cost(work orders) + extra_cost × qty  ==  Σ value(outputs done)
```

Verified empirically on real orders: it holds for a plain order, for both batches of a backorder and for a byproduct taking a cost share. It does **not** hold for a **standard cost** product — and that is exactly why it is checked instead of assumed.

If it does not hold, or the move belongs to no manufacturing order, or the native result does not have the shape the module knows, or **anything at all raises**, the module returns the **single counterpart line** the base module already produced. Never a half-written entry.

---

## Frequently asked questions

**The entry still shows one single credit line.**
Either no account is configured, or the cost of that order does not decompose (a standard-cost product, typically). In the second case the server log states it explicitly and the native counterpart is kept.

**Does the value of my product change?**
Never — not even when the labour entry is suppressed. Odoo puts the work centre cost into the value of the finished product regardless of whether that entry is posted. Quantities, values, average cost and the kardex are identical with and without this module.

**I ticked "No Accounting Entry" and lost my analytic cost accounting.**
You did not. Analytic entries are created when the **duration** of the work order is set, completely independently of the labour entry, so the analytic distribution of the work centre keeps working as in native Odoo.

**A balance is left in the production location account.**
The labour entry and the operations account are pointing at different places. Either tick **No Accounting Entry** on every work centre of the order, or clear the operations account.

**Does the consumable start generating its own consumption entry?**
No. The native `is_storable` guard is not lifted: a non-storable component still books nothing on consumption, exactly as in native Odoo. Its cost surfaces in the credit of the recognition entry, which is where it can be read without inventing a counterpart for something that was never capitalised.

---

## Resilience

| Risk | Behaviour |
|---|---|
| The cost of the order does not decompose | No split: the single native counterpart line, plus an explanatory log line |
| The move belongs to no manufacturing order | No split |
| The sum of the origins exceeds the value of the move, or any origin is negative | No split |
| The native line builder changes shape | No split |
| Any exception inside the breakdown | Caught: the single counterpart line stands |
| `_cal_cost()` gains arguments | The override mirrors the native signature (`date` included and forwarded) and stays multi-record |

Verified by running the **native** test suites with the module installed and unconfigured: `mrp_account` **34/34**, `stock_account` **189/189** and `account` **976/976** green, plus **18/18** of the module's own tests and **38/38** of the base module.

> An adversarial review of this module found 8 defects while its own tests were green — one of them broke the native WIP accounting wizard. The only signal was running the **native** suites with the module installed. Repeat them after any change to the hooks.

---

## Technical notes

* **Depends on**: `account_reclassification`, `mrp_account`. `auto_install = True`.
* **Hooks**: `stock.move._reclass_counterpart_lines()` (extension point of the base module), `mrp.production._post_labour()`, `mrp.workorder._cal_cost(date)`. All of them call `super()` first.
* `_post_labour()` is not reimplemented: the cost of the flagged work centres is neutralised **only for the duration of that call**, through a context flag read by `_cal_cost()`. `_cal_price()` calls it without that context, which is why valuation is untouched.
* **New fields**: `product.template.reclass_recognition_account_id` / `reclass_operations_account_id`, the same two on `product.category`, and `mrp.workcenter.reclass_skip_labour_entry`.
* **No new models**, no new menus, no new security groups, no new entries.

### Running the tests

```bash
docker exec odoo19_app bash /odoo_dev/logs/direct_test.sh account_reclassification_mrp
# Non-regression over the native suites (run them in series):
docker exec odoo19_app bash /odoo_dev/logs/direct_test.sh account_reclassification_mrp mrp_account
docker exec odoo19_app bash /odoo_dev/logs/direct_test.sh account_reclassification_mrp stock_account
docker exec odoo19_app bash /odoo_dev/logs/direct_test.sh account_reclassification_mrp account
```

---

## Compatibility

* Odoo **19** — Enterprise, Odoo.SH, Ganemo Online / Ganemo.SH.
* **Not** supported on Odoo Online (custom code restrictions).
* Languages: English and Spanish (`es`).

---

**Author**: [Ganemo](https://www.ganemo.com)

**License**: OPL-1
