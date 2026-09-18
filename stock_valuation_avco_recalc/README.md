# **Stock Valuation Rebuild**
<img src="static/description/banner.png" width="100%" alt="Banner">

**Bring historical stock values back to what Odoo's own valuation engine gives them — without rewriting the periods you already reported.**

Odoo 19 stores a value on every stock movement, and every valued report reads it. When that history was built before late revaluations were handled (freights, bills at another price, subcontractor bills arriving after the goods left), or when values were damaged by hand, the stored values of the deliveries no longer match what the engine says.

This module rebuilds them with the **same engine** that `stock_landed_cost_variance` uses for every late revaluation.

---

## What a rebuild does

| | |
|---|---|
| Deliveries | Rewritten to the cost Odoo's own engine gives them, in date order (average, FIFO, lots, consignment) |
| Customer returns | Re-derived with Odoo's own method from their restated delivery |
| Value Odoo drops (goods arriving on negative stock, FIFO lots) | Recorded as a dated amount on the movement where it happens |
| Every amount | Recorded with the **Known From** date: periods before it keep the values they were reported with, and the difference prints in the period of that date (PLE 13.1 and 3.7 included) |
| Product cost | Refreshed by Odoo itself |
| Audit | Value before and after of every movement, not editable by anyone |

## What it does not do

| | Why |
|---|---|
| Post journal entries | A rebuild corrects history whose accounting was closed with other numbers: the differences are left visible for the accountant instead of being posted by surprise |
| Accept a date inside a locked period | A locked period must keep the values it was closed with |
| Delete manual valuations | They are deliberate |
| Use its own algorithm | It reuses the engine, which is checked against Odoo's stored values in parity tests |

---

## How to use it

1. **Inventory ▸ Reporting ▸ Moves Analysis**, filter the products to rebuild and select their movements.
2. **Action ▸ Rebuild Stock Valuation**.
3. Choose **Known From** (by default, today) and click **Rebuild**.
4. Review the audit: **Inventory ▸ Configuration ▸ Valuation Rebuild History**.

---

## Upgrading from 19.0.2

Version 19.0.3 retires the *adjustment* and *restatement* modes, the waterfall algorithm, the SQL write of the product cost and the deletion of valuation anchors. Audits of 19.0.2 are kept.

Corrections recorded by the old adjustment mode are **not** rebuilt during the upgrade — that would change past valuations without anyone asking. The upgrade log lists the products that carried them: run the rebuild on those, with a date agreed with the accountant.

---

**Author**: [Ganemo](https://www.ganemo.co)

**License**: OPL-1
