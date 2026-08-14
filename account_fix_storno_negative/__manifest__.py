{
    'name': 'Fix Storno Negatives',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': """Bulk-fix journal entries left with negative debit or credit by
                  Storno accounting, without resetting posted entries to draft.""",
    'description': """
Fix Storno Negatives
====================

When Storno (reversal) accounting is enabled by mistake, reversals and credit
notes post the amount as a negative in the natural debit/credit column instead
of a positive on the opposite side. Some localizations (e.g. Peru / SUNAT) do
not allow negative debit or credit, which breaks legal ledgers and reports.

This module adds an Action on Journal Entries that opens a confirmation wizard
showing how many lines and entries will be corrected (and how many selected
entries are ignored because they have no negatives). On confirm, it re-expresses
only the lines with negative debit or credit to the standard positive form,
deriving the correct column from the stored balance, and clears the sticky
is_storno flag on the fixed entries.

The fix is purely representational: balance, amount in currency, taxes and
reconciliations are untouched, so there is no need to reset posted entries to
draft and the electronic document is not affected.

Intended as a temporary utility: install it, run it over the selection, and
uninstall it.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': [
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/fix_storno_wizard_views.xml',
        'data/server_action.xml',
    ],
    'icon': '/account_fix_storno_negative/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 60.0,
    'module_type': 'official',
}
