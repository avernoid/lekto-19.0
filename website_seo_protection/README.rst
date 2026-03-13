**Website SEO Protection**
==========================

<img src="static/description/banner.png" width="100%" alt="Banner">

Stop Odoo appointment crawler traps before they exhaust your server resources. This module
implements multi-layer HTTP-level protection that blocks malicious bot requests immediately —
before any database query runs — and adds SEO-friendly noindex headers for calendar day pages.

---

## The Problem: Appointment Crawler Traps

Odoo's appointment pager generates URLs with a ``?domain=`` parameter containing a fresh
``datetime.datetime()`` value — unique every millisecond:

.. code-block::

    /appointment?domain=[('date','>=',datetime.datetime(2026,3,13,5,54,26,604179))]

Web crawlers follow every link they find. Because each of these URLs is unique, crawlers
generate **thousands of unique HTTP requests per minute**. Each request spins up an Odoo
worker, consumes memory, and eventually causes **OOM kills (signal 9)** — bringing your
server to its knees.

---

## Solution: Two Protection Layers

### Layer 1 — Block Crawler Trap (HTTP 404)

Detects and destroys trap URLs **before any Odoo code processes them**:

- Checks if the request path is an appointment URL (with or without language prefix).
- Inspects the ``?domain=`` query parameter for ``datetime`` patterns or URL-encoded colons.
- Returns **HTTP 404 immediately** — zero ORM load, zero DB queries.
- Also sets ``X-Robots-Tag: noindex`` on the 404 response.

**Pattern matched:**

.. code-block::

    /[lang/]appointment[/page/N]?domain=...datetime.datetime(...)...

### Layer 2 — Noindex Calendar Pages

For valid appointment calendar links that should not be indexed:

- Only applies to HTML responses for appointment paths with ``?date=`` or ``?datetime=``.
- Adds ``X-Robots-Tag: noindex, nofollow`` to the HTTP response header.
- No markup changes — safest approach, invisible to end users.

---

## Multilingual URL Support

Both layers use a compiled regex that matches all Odoo language prefixes:

.. code-block::

    /appointment              (no prefix)
    /en/appointment           (English)
    /es/appointment           (Spanish)
    /pt_BR/appointment        (Brazilian Portuguese)
    /zh-hans/appointment      (Simplified Chinese)
    /es/appointment/page/3    (paginated + lang)

---

## Installation

1. Install the module from the App Store or copy it to your ``addons`` path.
2. Go to **Apps** > Update Apps List > Search ``Website SEO Protection`` > **Install**.
3. ✅ No configuration needed. Protection is active immediately.

---

## Configuration

**None required.** There are no settings, no fields, no menus. The module operates entirely
at the HTTP dispatch layer — compatible with all Odoo website configurations.

---

## Technical Details

The implementation overrides ``ir.http._dispatch`` (class method). Both layers are implemented
as pure Python with no ORM calls:

- ``_is_appointment_path(cls, path)`` — regex match for path detection.
- ``_is_appointment_crawler_trap(cls)`` — query string analysis for Layer 1.
- ``_dispatch(cls, endpoint)`` — hook point, uses ``werkzeug.wrappers.Response`` for Layer 1.

The module depends only on ``website``. It is safe to install on any Odoo 18 website instance
regardless of whether the appointment module is installed.

---

## Dependencies

- ``website`` (Odoo native)

---

## Compatibility

- ✅ Odoo 18 Enterprise
- ✅ Odoo.SH
- ✅ Ganemo Online / Ganemo.SH
- ❌ Odoo.com (Odoo SaaS) — custom code not supported

---

## Languages

- 🇺🇸 English
- 🇪🇸 Spanish (es_ES, es_MX, es_PE)

---

## Author

**Author**: [Ganemo](https://www.ganemo.co)

**License**: OPL-1 (Odoo Proprietary License v1.0)

**Support**: help@ganemo.com

**Sales**: leads@ganemo.com | https://wa.me/18286726150
