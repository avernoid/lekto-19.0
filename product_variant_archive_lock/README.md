**Product Variant Archive Lock**

<img src="static/description/banner.png" width="100%" alt="Banner">

Two per-product controls to decide exactly which variants and which attribute
values are offered for sale — without losing data (stock, history, costs).

**Author**: [Ganemo](https://www.ganemo.com)

---

## What it does

Standard Odoo treats variants as **derived data**: whenever you add or change an
attribute or value, it regenerates the variant matrix through
`product.template._create_variant_ids` and **reactivates every still-valid
variant** — including the ones you archived by hand. That is deliberate, but it
leaves two practical gaps this module fills.

### 1. Keep manually archived variants archived

Opt in, **per product**, so the variants you archived by hand stay archived
after the matrix is regenerated. Brand-new combinations are still created and
activated as usual. The lock is **per exact combination**, not per value: if you
archive `Blue / M` and later add size `L`, the new `Blue / L` variant is created
active while `Blue / M` stays archived.

### 2. Hide attribute values from the order grid

A per-value flag (**Hide from order grid**) removes an attribute value — its
whole row or column — from the sales Order Grid (matrix) **without archiving,
deleting or recreating its variants**. The variants keep all their data, stock
and history and remain active; the value is only hidden from the grid, and the
setting survives later attribute edits. Ideal for large/seasonal catalogs: hide
discontinued or out-of-season designs so the grid stays clean, and bring them
back with a single click — no data loss.

## How it works

* **`product.template.variant_archive_lock`** (Boolean, per product, off by
  default) — switch for feature 1.
* **`product.product.manually_archived`** (Boolean, per variant) — set
  automatically when a user archives a variant from the UI (`action_archive`).
  The automatic archiving Odoo does for invalid combinations goes through a
  different path, so it is **not** flagged.
* **`product.template.attribute.value.hide_from_matrix`** (Boolean, per value) —
  switch for feature 2.
* Both features extend Odoo by calling `super()` and post-processing, never
  reimplementing native logic — resilient against upgrades. Feature 1 overrides
  `_create_variant_ids` to re-archive only the flagged variants. Feature 2
  overrides `_get_template_matrix` (via a context flag honored by a minimal
  `_only_active` override) to drop hidden values from the grid only, leaving
  variant generation untouched. Zero measurable cost for products that enable
  neither option.

## Configuration & usage

Enable the **Variants** feature in *Sales → Configuration → Settings* first.

**Feature 1 — Keep manually archived variants**
1. On the product form (*General Information*), tick **"Keep manually archived
   variants"**.
2. Archive the variants you do not want from the product's *Variants* list.
3. Editing attributes/values no longer revives them. To stop protecting a
   variant, un-archive it manually — the flag is cleared.

**Feature 2 — Hide from order grid**
1. Open the product → *Attributes* tab → **Configure** on an attribute line.
2. Open (or find) the value and tick **"Hide from order grid"**.
3. The value's row/column disappears from the Order Grid; its variants stay
   active. Untick to bring it back.

## When to use what

| Need | Tool |
|---|---|
| "This value never goes with that one" (pairwise rule) | Native Odoo **exclusions** |
| Remove an exact SKU in 3+ attribute products, keeping data | Feature 1 (archive + lock) |
| Make the manual archiving of variants persistent | Feature 1 |
| Hide a whole value (row/column) from the grid without archiving | Feature 2 |

Both features are **complementary** to native exclusions, not a replacement.

## Manifest

| Key | Value |
|---|---|
| Technical name | `product_variant_archive_lock` |
| Version | `19.0.1.0.3` |
| Depends | `product`, `sale_product_matrix` |
| License | `OPL-1` |

See [`__manifest__.py`](__manifest__.py) for the full declaration.

## Tests

```bash
# From the workspace root (auto-detects addons/)
powershell -ExecutionPolicy Bypass -File C:\odoo_dev_environment\run_odoo_tests.ps1 "product_variant_archive_lock"
```

12 tests. Feature 1: native baseline, lock keeps manual archiving, re-archive
touches only flagged variants, per-combination (multi-attribute) behavior,
manual un-archive clears the flag. Feature 2: matrix baseline, hide a column
value, hide a row value, variants not archived, `_only_active` unaffected
outside the matrix context, hiding a whole line does not crash, and the setting
persists after attribute edits.

## Cross-references

* Producer `agent-stack`: `odoopartners/agent-stack/awac.yml#repos`
* Odoo variant docs: <https://www.odoo.com/documentation/19.0/applications/sales/sales/products_prices/products/variants.html>
