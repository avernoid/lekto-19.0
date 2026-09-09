from odoo import models


class AccountReportLine(models.Model):
    _inherit = 'account.report.line'

    def _uses_analytic_domain_engine(self):
        """ True when every expression of the line is computed from analytic items, which
        is what decides the model its groupby has to be resolved against.
        """
        self.ensure_one()
        engines = set(self.expression_ids.mapped('engine'))
        return engines == {'analytic_domain'}

    def _parse_groupby(self, options, groupby_to_expand=None):
        """ The base implementation resolves the groupby field against account.move.line,
        which has no general_account_id nor analytic plan columns. Lines fed by the
        analytic_domain engine group analytic items instead.
        """
        if not self or not self._uses_analytic_domain_engine():
            return super()._parse_groupby(options, groupby_to_expand=groupby_to_expand)

        self.ensure_one()

        if groupby_to_expand:
            groupby_to_expand = groupby_to_expand.replace(' ', '')
            split_groupby = groupby_to_expand.split(',')
            current_groupby = split_groupby[0]
            next_groupby = ','.join(split_groupby[1:]) if len(split_groupby) > 1 else None
        else:
            current_groupby = None
            groupby = self._get_groupby(options)
            next_groupby = groupby.replace(' ', '') if groupby else None

        if current_groupby == 'id':
            groupby_model = 'account.analytic.line'
        elif current_groupby:
            # Raises a readable UserError instead of a KeyError on a misconfigured groupby.
            self.report_id._analytic_domain_check_groupby_fields([current_groupby])
            groupby_model = self.env['account.analytic.line']._fields[current_groupby].comodel_name
        else:
            groupby_model = None

        return {
            'current_groupby': current_groupby,
            'next_groupby': next_groupby,
            'current_groupby_model': groupby_model,
            'custom_groupby_map': {},
        }
