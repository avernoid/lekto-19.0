{
    'name': 'Stock Kardex Valued',
    'version': '19.0.1.0.1',
    'category': 'Inventory',
    'summary': 'Company-level valued inventory Kardex that reconciles with the General Ledger (GL).',
    'description': """
Stock Kardex Valued

A valued inventory Kardex (moving ledger) that is correct: it reconciles with
product.total_value (= quant.value = the stock valuation General Ledger), at company
level, and is fully generic (no dependency on any localization / SUNAT).

Values are re-simulated with the same recurrence Odoo core uses to compute total_value
(average via _run_average_batch / stock.avco.report, standard via _run_standard_batch,
FIFO via _run_fifo), NOT sum(move.value) which does not reconcile with the GL.

The three cost methods are supported (Average, Standard, FIFO) with a per-method
dispatcher. lot_valuated products are excluded. The report is a populated-per-run model
plus a wizard (period, filters, volume traffic-light), with List (grouped Template then
Product) and Pivot views.

The recon_delta column exposes the gap against a naive sum(move.value) ledger (what the
SUNAT PLE report would show), turning the divergence into an audit feature.

This module is intentionally independent from the SUNAT PLE report: it builds the correct
Kardex even where it differs from the official .txt (that is the point).
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': ['stock_account', 'stock_landed_costs'],
    'data': [
        'security/ir.model.access.csv',
        'security/stock_kardex_valued_security.xml',
        'data/ir_config_parameter.xml',
        'views/stock_kardex_valued_views.xml',
        'wizard/stock_kardex_valued_wizard_views.xml',
    ],
    'demo': [
        'data/demo/stock_kardex_valued_demo.xml',
    ],
    'icon': '/stock_kardex_valued/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 199.0,
    'module_type': 'official',
}
