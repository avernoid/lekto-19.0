# **Stock Value Variance**

<img src="static/description/banner.png" width="100%" alt="Banner">

When a landed cost, a vendor bill at another price or exchange rate, a subcontractor bill or a customer credit note changes the cost of goods that **have already left**, Odoo 19 corrects the product cost but **never the stored value of the deliveries**. Every report that reads that value stays wrong — the valued stock ledger, the Peruvian PLE 13.1 and 3.7, returns, point of sale, manufacturing, accruals, margins — and the accounting ends up split, with no identifiable cause, between the freight account, inventory and cost of sales.

This module corrects it **at the moment the event happens**, with one identified journal entry per event.

---

## The problem, measured

Receipt of 5 units at 500 (billed). Three units sold and invoiced. A landed cost of 250 is validated afterwards.

| | Odoo 19 | With this module |
|---|---|---|
| Stored value of the delivery | 1 500 | **1 650** |
| Sum of the valued ledger | 1 250 | **1 100** |
| Inventory value (`total_value`) | 1 100 | 1 100 |
| Stock valuation account | 1 100 | 1 100 |
| Cost of sales | 1 500 | **1 650** |
| Freight account | 150 left, unidentified | **0** |

---

## What happens at each event

For every product affected by the event:

1. **Deliveries are rewritten to the cost Odoo's own engine gives them today.** The cost is read from the native valuation engine, never computed in parallel: the native average replay, FIFO at the date of each delivery, the lot price at that date. Customer returns are re-derived with Odoo's own method.
2. **Every amount is recorded with the date of the event** (*Value Variances*), so any report can rebuild a past date exactly as it was known then.
3. **One journal entry, dated on the event, linked to its source document:**

| Line | Amount |
|---|---|
| Inventory | Inventory value change + part not yet costed − what Odoo already posted |
| Cost of sales, per sale line or point of sale session | Part of goods whose cost of sales was already posted |
| Production location account | Part consumed by manufacturing orders |
| Cost of sales, "negative stock" | Value Odoo's average replay drops when goods arrive on negative stock |
| Landed cost line account | Part of the landed cost Odoo did not capitalise |

The event is posted only if **revaluation = inventory value change + restated deliveries + negative stock change** holds. Otherwise it is recorded as *Inconsistent*, with no entry, and the native operation is never blocked.

4. **Manufactured goods follow**: finished products and by-products (by cost share) of the manufacturing or subcontracting orders that consumed the component are revalued with Odoo's own mechanism, and go through the same process.

---

## Events handled

| Event | Trigger |
|---|---|
| Landed cost | Validation |
| Vendor bill or credit note that revalues a receipt (price, exchange rate, subcontractor service) | Posting |
| Customer credit note (average cost) | Posting: the share of an earlier adjustment belonging to the returned units is reversed |
| Receipt on negative stock | Validation of the receipt |

**Not handled on purpose:** goods received not billed, billed not received, delivered not invoiced and invoiced not delivered are covered by Odoo's own accrual entries. Manual valuation adjustments post nothing in Odoo and post nothing here either.

---

## Cost of sales already posted is never counted twice

Odoo prices each new invoice's cost of sales as *cumulative quantity × cost today − cost of sales already posted on the sale line*. This module adds its adjustments to "already posted", so the next invoice of the same line does not recover the same amount again, and resetting an invoice to draft and posting it again changes nothing.

---

## Status of each event

**Inventory → Reporting → Late Revaluations**, and a smart button on landed costs and vendor bills.

| Status | Meaning |
|---|---|
| Posted | Its entry is posted |
| No Entry Needed | Odoo's own operation already posted everything (e.g. nothing had been sold) |
| Outdated | The entry or its source document was reset or cancelled: review it |
| Inconsistent | The event did not add up; no entry was posted |

Nothing is blocked and nothing is reversed silently.

---

## Supported

Average cost and FIFO, lot-valuated products (average and FIFO), consignment (owner stock), foreign currency purchases, point of sale (invoiced or not), manufacturing (finished goods, by-products, kits, unbuild), subcontracting, dropship (not affected: never in stock), negative stock, several landed costs, negative landed costs.

---

## Companion modules

| Module | What it adds |
|---|---|
| `stock_landed_cost_variance_kardex` | Kardex columns on stock moves read the stored value plus live amounts |
| `l10n_pe_reports_stock_transfer_document` | PLE 13.1 rebuilt as known at each period: a period already filed regenerates identically |
| `l10n_pe_reports_lib_stock_variance` | The same for the PLE 3.7 |
| `stock_valuation_avco_recalc` | Rebuilds historical data with the same engine |

---

## Upgrading from 19.0.1

Rows recorded by 19.0.1 are kept as history (kind *Legacy*) and ignored. Reclassification entries posted by 19.0.1 are kept and **not reversed**: review them. To bring the stored values of those products in line, run the valuation rebuild wizard of `stock_valuation_avco_recalc`.

---

## Operating advice

Register landed costs, vendor bills and subcontractor bills **before** posting accruals and generating period reports: accruals of goods delivered not invoiced read the stored value of the deliveries. Capturing the landed cost **before the first delivery**, with a provisioned estimate, avoids late revaluations altogether.

---

**Author**: [Ganemo](https://www.ganemo.com)

**License**: OPL-1
