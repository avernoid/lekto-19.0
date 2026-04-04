# -*- coding: utf-8 -*-
{
    'name': 'Button Control Per User',
    'version': '19.0.1.0.1',
    'icon': '/button_control_per_user/static/description/icon.png',
    'category': 'Extra Tools',
    'summary': 'Hide standard interface buttons per user without affecting permissions',
    'description': """
Button Control Per User
========================

This module allows administrators to hide standard interface buttons (New, Edit, Archive, 
Duplicate, Export, Import) on a per-user basis without modifying permissions or breaking 
native Odoo functionality.

Key Features:
-------------
* Hide buttons per user, not by security groups
* Context-aware rules (FSM, Sales, Readonly)
* No impact on users without rules (100% native behavior)
* Compatible with desktop and mobile
* Non-invasive extension (no core modifications)

Supported Buttons:
------------------
* New / Create
* Edit
* Archive / Unarchive
* Duplicate
* Export
* Import
* Delete
* Cancel
* Validate

Author: Ganemo
License: OPL-1
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'license': 'OPL-1',
    'images': ['static/description/banner.png'],
    'depends': [
        'web',
        'base',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/ui_button_rule_views.xml',
        'views/res_users_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'button_control_per_user/static/src/services/button_control_service.js',
            'button_control_per_user/static/src/search/action_menus/action_menus_patch.js',
            'button_control_per_user/static/src/views/kanban/kanban_controller_patch.js',
            'button_control_per_user/static/src/views/kanban/kanban_record_patch.js',
            'button_control_per_user/static/src/views/list/list_controller_patch.js',
            'button_control_per_user/static/src/views/form/form_controller_patch.js',
            'button_control_per_user/static/src/views/view_button/view_button_patch.js',
            'button_control_per_user/static/src/views/view_button/view_button.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'currency': 'USD',
    'price': 123.0,
    'module_type': 'official',
}
