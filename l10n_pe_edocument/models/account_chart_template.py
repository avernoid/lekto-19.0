from odoo import api, models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('pe', 'account.tax')
    def _get_pe_new_account_tax(self):
        return self._parse_csv('pe', 'account.tax', module='l10n_pe_edocument')
