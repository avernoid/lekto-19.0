# PLE Sale Book Tax Warning Debugging History

**Issue**: Critical warnings "Tax 'X' NOT FOUND" during module deployment/update.
**Date**: 2026-02-06
**Module**: `ple_sale_book` version 19.0.1.0.4

## Timeline & Actions

### 1. Initial Analysis
- **Symptoms**: Logs show failure to find taxes like `18%`, `Exo`, `Ina` despite them existing in the database for Company 1.
- **Strategies Tested**:
    1.  **Strict XML ID (Odoo 19)**: `l10n_pe.1_sale_tax_igv_18`
    2.  **Legacy XML ID**: `account.1_sale_tax_igv_18`
    3.  **Name Search**: Keyword matching (e.g., "IGV" + "18").
- **Observation**: All 3 strategies failed.

### 2. Hypothesis & Fixes (Applied)
- **Whitespace Sensitivity**: Suspected leading/trailing whitespace in tax names (e.g., " 18% ") caused exact string matches to fail.
    - **Fix Applied**: Added `.strip()` to tax names and keywords in `account_tax_tags.py`.
- **Search Context**: Suspected `active_test=True` might filter out necessary taxes if they were archived (though checks showed they were active).
    - **Fix Applied**: Forced `active_test=False` in the tax search.
- **Diagnostic Logging**: Added explicit logs (`PLE SALE BOOK DEBUG`) to list *exactly* what taxes are returned by the search query. This is the primary tool for next-step debugging if warnings persist.

### 3. "Reverted" Ideas (Known Pitfalls)
- **Clearing Tags (`(5,0,0)`)**:
    - **Idea**: Use `(5,0,0)` in `write()` to clear existing tags before adding new ones (to ensure idempotency and avoid duplicates). This pattern exists in `ple_sale_book_old`.
    - **Result**: **REVERTED**.
    - **Reason**: This causes crashes during **Demo Data** loading in Odoo (specifically when the module tries to update taxes while demo data is being generated/processed).
    - **Correction**: We reverted to the `tags = []` (additive only) approach to preserve stability during demo data loading.

### 4. Strategic Shift: Manual Configuration Wizard (Final Solution)
- **Problem**: Automatic tax matching during installation is fragile due to environment contexts (e.g., Odoo.sh vs Local) and data state (Demo mode).
- **Solution**: Implemented a **Data-Driven Configuration Wizard**.
    - **Model**: `ple.sale.tax.config` stores the mapping rules (Tax Code -> Tags).
    - **Data**: Pre-loaded standard Peruvian tax rules in `data/ple_sale_tax_config_data.xml`.
    - **UI**: Added a menu `Configuration -> Tax Configuration` where users can verify and edit mappings.
    - **Action**: A wizard `ple.update.tags.wizard` allows executing the update manually for the current company, providing immediate feedback.
- **Status**: Replaced the automatic hook with this manual, user-controlled process.

## Current State
- Code includes `.strip()` for robust name matching rules.
- Automatic hook is **DISABLED**.
- Configuration Menu is available.

## Next Steps
- Deploy and use the Wizard for setup.

