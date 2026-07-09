{
    "name": "Custom Work Order Report",
    "version": "19.0.1.4.0",
    "category": "Inventory/Delivery",
    "summary": "Print a corporate-branded Work Order PDF from stock pickings, "
    "reusing the header/footer layout of sale_corporate_quotation.",
    "description": """
Custom Work Order Report
========================

Generates a QWeb PDF report called "Orden de Trabajo" from any stock.picking,
reusing the corporate branding (header, footer, paper format) defined in the
sale_corporate_quotation module.

The report includes:
- Corporate header with logos, RUC, address and document code PR-VE-FT-012 Rev. 0
- General data: dates, customer, RUC, project
- Part 1: Product description table (item, product, qty, weight, description)
- Part 2: Shipping details (delivery contact)
- Part 3: Observations (free-text field added to sale.order)
- Corporate footer

No new fields are added to stock.picking; all data is derived from existing
fields or related models. Only one new field (work_order_observations) is
added to sale.order.
""",
    "author": "Ganemo",
    "maintainer": "Ganemo",
    "company": "Ganemo",
    "website": "https://www.ganemo.co",
    "depends": [
        "stock",
        "sale_stock",
        "sale_corporate_quotation",
        "sale_custom_fields",
    ],
    "data": [
        "report/report_action.xml",
        "report/report_work_order.xml",
        "views/res_partner_views.xml",
        "views/sale_order_views.xml",
        "views/stock_picking_views.xml",
    ],
    "icon": "/custom_work_order/static/description/icon.png",
    "images": ["static/description/banner.png"],
    "license": "OPL-1",
    "installable": True,
    "auto_install": False,
    "application": False,
    "currency": "USD",
    "price": 59.0,
    "module_type": "official",
}
