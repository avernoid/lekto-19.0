{
    'name': 'FSM Reports',
    'version': '19.0.1.0.6',
    'category': 'Field Service',
    'summary': 'Advanced analytical reports for Field Service visit effectiveness and sales conversion',
    'description': """
        Advanced SQL-based analytical reports for FSM tasks.
        Includes Efectividad de Visitas, Conversión → Venta, and Análisis de Ventas
        reports accessible from Field Service → Reporting.
        Supports row-level security: FSM Users see only their own visits;
        FSM Managers see all records.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': [
        'industry_fsm',
        'industry_fsm_sale',
        'auto_cancel_fsm_task',
        'fsm_sale_lost_reason',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'views/report_fsm_task_visit_views.xml',
        'views/menus.xml',
    ],
    'icon': '/fsm_reports/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 149.0,
    'module_type': 'official',
}
