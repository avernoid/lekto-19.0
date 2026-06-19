{
    "name": "Sale Project Auto Create",
    "version": "19.0.1.0.1",
    "category": "Sales/Sales",
    "summary": """Create a project (with its analytic account) on sales order """
    """confirmation by policy, without needing a service product line.""",
    "description": """
Sale Project Auto Create
========================

Natively, Odoo only creates a project from a sales order when the order
contains a *service* product whose ``service_tracking`` is configured to
generate one (``Project``/``Project & Task``). That forces a product line on
the quotation -- even a zero-priced one still shows up -- when all you want is
to govern *one project per sales order*.

This module decouples project creation from the catalogue. On confirmation,
if the order is flagged for it, a project is created and linked to the order
(``project_id``) together with its analytic account -- exactly the same
plumbing the native flow produces, but triggered by policy instead of by a
product line.

Trigger

- A sales team boolean ("Create Project on Sales Confirmation") sets the default policy.
- A per-order boolean (in the Other Info tab) inherits that default and can be overridden on each order.

Safe by construction

- It runs before native confirmation, so the stock procurement carries the project just like the native service-product flow.
- It never collides with the native generation: if any order line is a service product configured to generate a project or task, this module stays out of the way. It also does nothing when the order already has a project.
- It reuses the native helpers and the native project wiring, so it follows upstream behaviour rather than reimplementing it. If the order already generates a project the module is a harmless no-op.
""",
    "author": "Ganemo",
    "maintainer": "Ganemo",
    "company": "Ganemo",
    "website": "https://www.ganemo.co",
    "depends": [
        "sale_project",
    ],
    "data": [
        "views/crm_team_views.xml",
        "views/sale_order_views.xml",
    ],
    "icon": "/sale_project_auto_create/static/description/icon.png",
    "images": ["static/description/banner.png"],
    "license": "OPL-1",
    "installable": True,
    "auto_install": False,
    "application": False,
    "currency": "USD",
    "price": 120.0,
    "module_type": "official",
}
