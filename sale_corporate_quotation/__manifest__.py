{
    "name": "Corporate Sales Quotation PDF",
    "version": "19.0.1.0.3",
    "category": "Sales",
    "summary": "Print sales quotations with a configurable corporate PDF layout: "
    "logos, certification seal, document code, payment block and delivery time.",
    "description": """
Corporate Sales Quotation PDF
=============================

Replace the standard Odoo quotation with a professional, corporate-branded PDF
that you configure once per company.

Header
------
- Company logo + optional certification seal (ISO / SGS / UKAS).
- Optional internal document code (e.g. a form code), shown top-right.
- RUC / address / phone and page numbering on every page.

Body (four parts)
-----------------
- Part 1 - Description / Costs: items, sections, notes and totals (with tax).
- Part 2 - Payment Details: payment term, validity, account holder (the company
  name) and a free per-company HTML block for bank accounts and conditions.
- Part 3 - Delivery Time & Place: delivery address and the lead time expressed
  in working days (from the bundled sale_delivery_lead_workdays dependency).
- Part 4 - Terms & Conditions: the order notes.

Per-company configuration
--------------------------
All branding lives on the company (Settings > Companies > Corporate Quotation):
payment block, certification logo, footer phone/email icons and document code.
Every field is optional and degrades gracefully when empty.

Multi-language: English interface with Spanish translation included.
""",
    "author": "Ganemo",
    "maintainer": "Ganemo",
    "company": "Ganemo",
    "website": "https://www.ganemo.co",
    "depends": [
        "sale_management",
        "sale_delivery_lead_workdays",
        "web",
    ],
    "data": [
        "views/res_company_views.xml",
        "report/report_action.xml",
        "report/report_corporate_quotation.xml",
    ],
    "icon": "/sale_corporate_quotation/static/description/icon.png",
    "images": ["static/description/banner.png"],
    "license": "OPL-1",
    "installable": True,
    "auto_install": False,
    "application": False,
    "currency": "USD",
    "price": 89.0,
    "module_type": "official",
}
