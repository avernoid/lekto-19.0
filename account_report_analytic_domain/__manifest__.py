{
    'name': "Analytic Domain Report Engine",
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': """Report lines that sum the distributed share of analytic items""",
    # Flush-left on purpose: Odoo renders this through docutils, and a single indented
    # line raises "Unexpected indentation", which turns an Odoo.SH build red.
    'description': """
Analytic Domain Report Engine

Adds an "Analytic Domain" computation engine to Odoo's native report builder. It is the
counterpart of the built-in "Odoo Domain" engine: you write a domain and the engine sums
the matching records, except it runs on analytic items instead of journal items.

A report line built on journal items can filter by analytic distribution, but it always
brings the full balance: an expense of 1,000 split 20% Marketing / 30% Administration /
50% Management shows 1,000 on a line meant to show 800. This engine shows 800, because an
analytic item already carries the share Odoo distributed to it. No arithmetic is added.

Formulas are ordinary Odoo domains on the fields of Analytic Items: the analytic account
of a plan, the accounting account with its type, code or tags, the partner, the product,
the journal and the date. Dates and every date scope, companies, journals, partners and
currency conversion are taken from the report itself. Lines can be grouped by any stored
analytic field, and auditing a figure opens the analytic items behind it.

Two banners in the expression form list this database's own analytic plans with the field
each one answers to, and review the formula as it is typed, separating what will not work
from what will merely be slow.

Requires Accounting Reports (Enterprise).
""",
    'author': "Ganemo",
    'maintainer': "Ganemo",
    'company': "Ganemo",
    'website': "https://www.ganemo.co",
    'depends': [
        'account_reports',
        'analytic',
    ],
    'data': [
        'views/account_report_expression_views.xml',
    ],
    'demo': [
        'demo/account_report_analytic_domain_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'account_report_analytic_domain/static/src/components/**/*',
        ],
    },
    # Authored as .svg, shipped as .png — the store reads the .png variants.
    'icon': '/account_report_analytic_domain/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 149.0,
    'module_type': 'official',
}
