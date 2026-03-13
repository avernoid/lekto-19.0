**Website SEO Protection: Appointment**

<img src="static/description/banner.png" width="100%" alt="Banner">

## Overview

This is a **companion bridge module** for [Website SEO Protection](https://apps.odoo.com/apps/modules/18.0/website_seo_protection/).
It auto-installs alongside `website_appointment` and provides **multi-layer HTTP-level protection** against
Odoo appointment URL crawler traps that can exhaust your server resources.

---

## The Problem

Odoo's appointment module generates URLs with dynamic parameters that create **crawler traps**:

- **`?domain=`**: Contains ORM domain filters. Bots generate infinite combinations (e.g., `?domain=[('user_id','=',1)]`), causing thousands of unique page fetches that saturate your server CPU and memory.
- **`?date=` / `?datetime=`**: Calendar navigation parameters that create hundreds of functionally identical pages, hurting SEO by diluting your page authority.

Without protection, a single malicious or over-enthusiastic bot crawl can bring down an Odoo instance.

---

## Solution: Two Layers of Protection

### Layer 1 — HTTP 404 (Blocks the Loop)

Any request to an appointment URL containing the `?domain=` parameter receives an **HTTP 404** response immediately.

- Operates at the **WSGI middleware level** — before Odoo's ORM or controllers process the request.
- No database queries, no template rendering. Maximum performance.
- Legitimate users are never affected (real appointments never use `?domain=` in the URL).

### Layer 2 — X-Robots-Tag: noindex (SEO Clean-Up)

Appointment calendar URLs with `?date=` or `?datetime=` receive the HTTP response header:

```
X-Robots-Tag: noindex, nofollow
```

- Signals Google and other bots to **skip indexing** these navigation-only pages.
- Delivered via **HTTP header** (not HTML meta tag), so it works even on dynamic/JS pages.
- Human visitors see no difference — the calendar navigates normally.

---

## Auto-Install Behavior

This module has `auto_install: True`. It activates **automatically** when both:

- `website_seo_protection` (the core module), AND
- `website_appointment`

...are installed in the same Odoo database.

No manual installation or configuration is required. This follows Odoo's official convention for bridge/companion modules.

---

## Multilingual URL Support

All protections work for **all Odoo language-prefixed URL formats**:

- `/web/appointment/1?domain=...` → 404
- `/en/web/appointment/1?domain=...` → 404
- `/es/web/appointment/1?date=2024-01-01` → X-Robots-Tag: noindex
- `/pt_BR/web/appointment/1?datetime=2024-01-01` → X-Robots-Tag: noindex

---

## Dependencies

| Module | Purpose |
|---|---|
| `website_seo_protection` | Core middleware — provides the HTTP interception layer |
| `website_appointment` | Triggers auto-install; provides the appointment URL routes |

---

## Installation

1. Install `website_seo_protection` (the core module).
2. Install `website_appointment` (Odoo's native appointment module).
3. This module will install **automatically** — no action needed.

To verify: go to **Settings → Technical → Installed Modules** and search for `website_seo_protection_appointment`.

---

## QA / Validation

### Test 1 — Layer 1 (404 for ?domain=)

```
URL: /web/appointment/1?domain=[('user_id','=',1)]
Expected: HTTP 404 response
Normal URL: /web/appointment/1 → loads normally ✓
```

### Test 2 — Layer 2 (noindex for ?date=)

```
URL: /web/appointment/1?date=2024-03-15
Check Response Headers → X-Robots-Tag: noindex, nofollow ✓
Same URL without ?date= → no X-Robots-Tag header ✓
```

### Test 3 — Multilingual

```
URL: /es/web/appointment/1?domain=[('user_id','=',1)]
Expected: HTTP 404 ✓
URL: /en/web/appointment/1?date=2024-03-15
Expected: X-Robots-Tag: noindex, nofollow ✓
```

---

## Compatibility

| Platform | Status |
|---|---|
| Odoo.SH (Enterprise) | ✅ Supported |
| Ganemo Online / Ganemo.SH | ✅ Supported |
| Odoo Online (SaaS) | ❌ Not supported (custom modules not allowed) |
| Odoo Community | ✅ Supported (if website_appointment is available) |

---

## Author

**Author**: [Ganemo](https://www.ganemo.co)

- 🌐 Website: [ganemo.co](https://www.ganemo.co)
- 💬 WhatsApp: [+1 (828) 672-6150](https://wa.me/18286726150)
- 📧 Sales: leads@ganemo.com
- 🎫 Support: help@ganemo.co
- 📅 Book a Demo: [ganemo.co/appointment/5](https://www.ganemo.co/appointment/5)
