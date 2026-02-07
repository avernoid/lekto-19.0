{
    'name': 'View Multicompany Country Filter',
    'version': '19.0.0.0.0',
    'author': 'Ganemo',
    'website': 'https://www.ganemo.com',
    'category': 'Contacts',
    'module_type':'official',
    'summary': 'Hides specific fields in views depending on localization',
    'description': """
This module provides a technical mixin to dynamically control the visibility of XML fields 
in views based on the company's country.

Key Features:
- **Dynamic Visibility**: Hides fields/groups in Form, List, and Kanban views if they don't belong to the active company's country.
- **Smart Caching**: Uses `view.multicompany.country.filter.mixin` to segment view caches by company, preventing cross-company UI pollution.

Usage:
1. Inherit `view.multicompany.country.filter.mixin` in your model (REQUIRED).
2. Override `_get_view` and call `_tags_invisible_per_country`.

Example:
    class ResPartner(models.Model):
        _inherit = ['res.partner', 'view.multicompany.country.filter.mixin']

        def _get_view(self, ...):
            # ... checks ...
            arch, view = self._tags_invisible_per_country(..., tags=['my_field'], countries=[peru])
            return arch, view
    """,
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'depends': [
        'base'
    ],
    'images': ['static/description/banner.png'],
    'application': False,
    'installable': True,
    'auto_install': False,
    'icon': '/view_multicompany_country_filter/static/description/icon.png',
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 0.00,
}
