{
    "name": "Sale Custom Fields",
    "version": "19.0.1.4.0",
    "category": "Sales",
    "summary": "Centralized custom fields for quotations and sale orders.",
    "description": """
Sale Custom Fields
==================

Adds informational fields to the quotation / sale order form so that
salespeople can record data useful for the rest of the organisation:

* **Description** – short summary that identifies a quotation at a glance
  in list views and queues.
* **Customer Purchase Order** – the customer's purchase-order number once
  they confirm the sale.
* **Work-Order Observations** – free-text notes printed on the Work Order
  report (Orden de Trabajo).
""",
    "author": "Ganemo",
    "maintainer": "Ganemo",
    "company": "Ganemo",
    "website": "https://www.ganemo.co",
    "depends": [
        "sale",
    ],
    "data": [
        "views/sale_order_views.xml",
    ],
    "icon": "/sale_custom_fields/static/description/icon.png",
    "images": ["static/description/banner.png"],
    "license": "OPL-1",
    "installable": True,
    "auto_install": False,
    "application": False,
    "currency": "USD",
    "price": 40.0,
    "module_type": "official",
}
