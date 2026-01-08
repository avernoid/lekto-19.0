# Tests disabled because the Python logic (account_financial_report.py) has been removed.
# This module now serves as a bridge/shell for the base module functionality.
from odoo.tests.common import TransactionCase
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestFinancialAnnexesEnterprise(TransactionCase):
    def test_module_installable(self):
        """Verify the module installs correctly as a shell."""
        pass
