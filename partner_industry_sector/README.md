# **Partner Industry Sector**

<img src="static/description/banner.png" width="100%" alt="Banner">

Classify your contacts by **industry sector** (*rubro*) in Odoo. This module adds a
configurable sector catalog and a smart field on contacts so you can segment, filter
and group your customer base by industry — ideal for CRM targeting, marketing lists
and management reporting.

---

## Overview

Out of the box, Odoo has no dedicated, company-controlled "industry sector" field on
contacts. **Partner Industry Sector** fills that gap by adding:

- A centralized **Industry Sector** catalog (model `industry.sector`).
- A **Sector / Rubro** field on every contact (`res.partner.industry_sector_id`) —
  companies and their contacts alike. On a contact it is pre-filled from the parent
  company on creation, yet can be changed independently.
- A **"Set Industry Sector from parent company"** mass action to realign selected
  contacts with their company's sector in one click.
- A **search filter** and a **Group By** option on the Contacts list, so you can analyze
  your contacts by industry instantly.

Because every sector comes from the same catalog (with a unique-name rule), your data
stays clean and your reports stay comparable across the whole company.

---

## Features

| Feature | Description |
|---|---|
| **Sector catalog** | Manage the list of industry sectors from one place. Names are unique and translatable; sectors can be archived instead of deleted. |
| **Contact classification** | A `Sector / Rubro` field on the contact form lets you assign an industry to any contact — companies and individuals alike. |
| **Inherit from the company** | New contacts are pre-filled with their parent company's sector on creation (imports included), but you can override the value per contact. |
| **Bulk realign** | A *Set Industry Sector from parent company* mass action on the Contacts list overwrites the selected contacts' sector with their company's. |
| **Filter & Group By** | Filter contacts by sector and group the Contacts list by `Sector / Rubro` for fast segmentation. |
| **Demo data** | 18 common industry sectors are preloaded as demo data to get you started. |
| **Multi-language** | English source with Spanish translation included (`es`). |

---

## Requirements

- **Odoo version:** 19.0
- **Dependencies:** `contacts`, `account`, `sale` (installed automatically).

---

## Installation

1. Copy the `partner_industry_sector` folder into your Odoo `addons` path.
2. Activate **Developer Mode** (optional, for the *Update Apps List* action).
3. Go to **Apps**, update the apps list, search for *Partner Industry Sector* and click **Install**.

---

## Configuration

The module is ready to use right after installation. To curate your own sector list:

1. Open the **Sales** app.
2. Go to **Configuration → Industry Sectors**.
3. Add, rename or **archive** sectors directly from the editable list view.

> **Note:** Sector names must be unique. If you try to create a duplicate, Odoo blocks it
> with a clear message. Names are translatable, so the same catalog reads correctly in
> English and Spanish.

---

## Usage

### 1. Classify a contact

1. Open any contact — a company or an individual.
2. Set the **Sector / Rubro** field on the contact form and save.

> When you set a contact's parent company, the sector is pre-filled from that company
> automatically (on creation and on import). You can change it afterwards, or use the
> **Set Industry Sector from parent company** mass action to realign several contacts at
> once.

### 2. Segment your contacts

1. Go to the **Contacts** list view.
2. Use the **Sector / Rubro** filter to narrow down to a single industry, **or**
3. Use **Group By → Sector / Rubro** to see how your customers break down by sector.
   Contacts without a sector appear in their own group.

---

## Access Rights

| Role | Read | Create / Edit / Archive |
|---|:---:|:---:|
| Internal Users | ✅ | ❌ |
| Contact Managers | ✅ | ✅ |

All internal users can read and assign sectors; only **Contact Managers** can manage the
catalog itself.

---

## Technical Notes

- **New model:** `industry.sector` — fields `name` (unique, translatable) and `active`.
- **Inherited model:** `res.partner` — adds `industry_sector_id` (Many2one to
  `industry.sector`), pre-filled from `parent_id` via an `onchange` and on `create`
  (so imports inherit it too).
- **Server action:** *Set Industry Sector from parent company*
  (`action_inherit_industry_from_parent`) — a list-view mass action that copies the
  parent company's sector onto the selected contacts.
- **Views:** editable list + form for the catalog; the partner form and search views are
  extended to add the field, filter and Group By.
- **Menu:** *Sales → Configuration → Industry Sectors*.

---

## Support

| Channel | Contact |
|---|---|
| Sales / Commercial | leads@ganemo.com · WhatsApp +1 (828) 672-6150 |
| Technical Support | ayuda@ganemo.com |
| Book a Demo | https://www.ganemo.co/appointment/5 |

---

**Author**: [Ganemo](https://www.ganemo.com)

**License**: Odoo Proprietary License v1.0 (OPL-1)
