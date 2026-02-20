# **GitHub Product Document**

<img src="static/description/banner.png" width="100%" alt="Banner">

## Overview

Link product variants to GitHub repository branches and deliver downloadable module ZIP files to customers automatically using Odoo's native `product.document` system.

When a sale order is confirmed, the customer sees the download link in their portal — no manual intervention needed.

---

## Key Features

| Feature | Description |
|---|---|
| **Branch Linking** | Each product variant can be linked to a `github.repository.branch` |
| **One-Click Sync** | Button in form view fetches ZIP via GitHub API |
| **Batch Sync** | Select multiple variants in list view and sync all at once |
| **Staleness Detection** | Repo sync automatically marks linked variants as "Needs Update" |
| **Background Cron** | Scheduled action every 12h refreshes stale ZIPs |
| **Native Delivery** | Uses `product.document` with `attached_on_sale='sale_order'` |

---

## Dependencies

- `github_connector` — GitHub API integration and branch management
- `sale` — Sale order confirmation triggers document visibility

---

## Configuration

### 1. Prerequisites

Ensure the **GitHub Connector** module is installed and configured with:
- A valid GitHub organization
- An access token with repository read permissions
- Synced repositories and branches

### 2. Link Variants to Branches

1. Go to **Sales > Products > Product Variants**
2. Open a variant (e.g., version "18.0")
3. Set the **GitHub Branch** field to the matching branch (e.g., `18.0`)

### 3. Generate ZIP

- **Single variant:** Click **"Sync GitHub Doc"** in the form header
- **Multiple variants:** Select in list view → **Action > Sync GitHub Doc**

### 4. Verify

- Check that a `product.document` record was created for the variant
- The `attached_on_sale` field should be `sale_order`
- The `Needs Update` flag should be `False`

---

## How It Works

```
Product Variant (18.0)
    └── github_branch_id → github.repository.branch (18.0)
            └── GitHub API → get_archive_link("zipball", "18.0")
                    └── Download ZIP → base64 encode
                            └── product.document (attached_on_sale='sale_order')
                                    └── Customer confirms order → sees download
```

### Automatic Staleness

When **GitHub Organization > Sync Repositories** runs:
1. The system detects updated repositories
2. Finds all product variants linked to branches of that repository
3. Sets `github_doc_needs_update = True` on each variant

### Cron Auto-Refresh

Every 12 hours, the scheduled action **"GitHub: Update Stale Product Documents"**:
1. Searches for variants with `needs_update = True`
2. Downloads fresh ZIPs from GitHub
3. Updates `product.document` records
4. Resets `needs_update = False`

---

## FAQ

**Q: The sync button doesn't appear?**
A: The button is only visible when a **GitHub Branch** is assigned to the variant. Set the field first.

**Q: ZIP download fails with a timeout?**
A: The system has a 120-second timeout. For very large repositories, let the cron handle it or sync during off-peak hours.

**Q: Customer doesn't see the download?**
A: The document uses `attached_on_sale='sale_order'`. The download is only visible after the sale order is **confirmed** (not just quoted).

**Q: Does this work with private repositories?**
A: Yes. The module uses the same GitHub access token configured in the GitHub Connector module.

---

## Compatibility

- **Odoo Version:** 18.0
- **Edition:** Enterprise (Odoo.SH, Ganemo Online)
- **Languages:** English, Spanish

---

**Author**: [Ganemo](https://www.ganemo.com)
