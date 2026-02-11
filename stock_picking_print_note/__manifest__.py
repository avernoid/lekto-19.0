{
    'name': 'Print note on Warehouse guide',
    'version': '19.0.1.0.0',
    'author': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'summary': 'Includes Inventory Transfer Notes in printed format',
    'description': """
In the format for printing the delivery voucher, the Notes field and fields 
for the signature of those involved in the transfer are added.
""",
    'category': 'Warehouse',
    'depends': ['stock'],
    'data': ['static/src/xml/qweb_templates.xml'],
    'installable': True,
    'module_type': 'official',
    'auto_install': False,
    'application': False,
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 15.00,
    'images': ['static/description/banner.png'],
    'icon': '/stock_picking_print_note/static/description/icon.png',
}
