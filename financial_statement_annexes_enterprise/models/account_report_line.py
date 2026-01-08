import re
from odoo import models


class AccountReportLine(models.Model):
    _inherit = 'account.report.line'

    def _expand_groupby(self, line_dict_id, groupby, options, offset=0, limit=None, load_one_more=False, unfold_all_batch_data=None):
        group_lines = super()._expand_groupby(line_dict_id, groupby, options, offset, limit, load_one_more, unfold_all_batch_data)
        for line in group_lines:
            if line.get('caret_options') == 'account.account':
                id_str = line.get('id', '')
                account_id_str = re.search(r'~account\.account~(\d+)', id_str)                
                if account_id_str:
                    account_id = int(account_id_str.group(1))
                    obj_account = self.env['account.account'].browse(account_id)
                    line.update({
                        'account_id': obj_account.id,
                        'reconcile': obj_account.reconcile
                    })
        return group_lines
