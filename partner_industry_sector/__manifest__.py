{
    "name": "Partner Industry Sector",
    "version": "19.0.1.2.0",
    "category": "Contacts",
    "summary": "Classify contacts by industry sector (rubro) and segment customers by industry.",
    "description": """
Partner Industry Sector
========================

Adds a configurable industry-sector (rubro) classification to your contacts.

Key features:

* New "Industry Sector" catalog (model ``industry.sector``) managed from
  Sales > Configuration, with unique names, archiving and translations.
* New "Industry Sector" field on every contact (companies and their
  contacts), pre-filled from the parent company on creation but freely
  editable per contact.
* "Set Industry Sector from parent company" mass action to realign the
  selected contacts with their company's sector.
* Search filter and "Group By" on the Contacts list to segment your
  customer base by industry for CRM, marketing and reporting.
* Ships with 18 common industry sectors as demo data.
""",
    "author": "Ganemo",
    "maintainer": "Ganemo",
    "company": "Ganemo",
    "website": "https://www.ganemo.co",
    "depends": [
        "contacts",
        "account",
        "sale",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/industry_sector_views.xml",
        "views/res_partner_views.xml",
    ],
    "demo": [
        "demo/industry_sector_demo.xml",
    ],
    "icon": "/partner_industry_sector/static/description/icon.png",
    "images": ["static/description/banner.png"],
    "license": "OPL-1",
    "installable": True,
    "auto_install": False,
    "application": False,
    "currency": "USD",
    "price": 10.0,
    "module_type": "official",
}
