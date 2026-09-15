from markupsafe import Markup

from odoo import _, models

from .account_report_expression import _code

# Timings of the native 'domain' engine, measured with EXPLAIN (ANALYZE) on a production
# database (218k journal items, 7.6k accounts), one fiscal year, warm cache, over the filter
# the engine always adds (company, posted, not a section/note). Shown as orders of
# magnitude. They are journal-item figures: the analytic ones in account_report_expression
# come from a different, smaller table and must not be reused here.
COST_AML_COLUMN = "~5 ms"          # account_id in ids, partner_id, journal_id
COST_AML_ANALYTIC = "~3 ms"        # analytic_distribution, through its GIN index
COST_AML_ACCOUNT_FIELD = "~35 ms"  # account_id.account_type: a join to account_account
COST_AML_ACCOUNT_CODE = "~10 ms"   # account_id.code: code_store jsonb, per company
COST_AML_MOVE = "~45 ms"           # move_id.<field>: a join to account_move
COST_AML_X2MANY = "~45 ms"         # tax_tag_ids and other x2many: one EXISTS per item
COST_AML_BATCH = "~36 ms"          # every line rooted on account_id, all in one query


class AccountReportExpression(models.Model):
    _inherit = 'account.report.expression'

    # ------------------------------------------------------------------
    # Guide
    # ------------------------------------------------------------------
    def _domain_engine_guide(self):
        self.ensure_one()
        return Markup(
            '<div class="alert alert-info mb-0" role="status">'
            '<p class="mb-2"><b>%(title)s</b> %(intro)s</p>'
            '<p class="mb-1">%(fields_intro)s</p>'
            '<ul class="mb-2">'
            '<li>%(c_account)s — %(account)s</li>'
            '<li>%(c_natives)s — %(natives)s</li>'
            '<li>%(c_move)s — %(move)s</li>'
            '<li>%(c_analytic)s — %(analytic)s</li>'
            '</ul>'
            '<p class="mb-1">%(batch)s</p>'
            '<p class="mb-1">%(examples)s</p>'
            '<pre class="mb-0">%(sample1)s\n%(sample2)s\n%(sample3)s</pre>'
            '</div>'
        ) % {
            'title': _("This formula filters journal items."),
            'intro': _(
                "Each matching journal item counts with its full balance, even when its "
                "analytic distribution splits it across several analytic accounts. "
                "Subformula: sum, -sum, sum_if_pos, sum_if_neg or count_rows."
            ),
            'fields_intro': _("Useful fields:"),
            'c_account': _code('account_id'),
            'account': _("the accounting account, and through it its type, code or tags."),
            'c_natives': Markup(', ').join(_code(n) for n in ('partner_id', 'journal_id', 'date')),
            'natives': _("columns of the journal item itself, the cheapest to filter on."),
            'c_move': _code('move_id.<field>'),
            'move': _("anything on the journal entry. It costs a join for every line."),
            'c_analytic': _code('analytic_distribution'),
            'analytic': _(
                "filters by analytic account but never prorates. To get the distributed share, "
                "use the Analytic Domain engine."
            ),
            'batch': _(
                "Lines whose conditions all start from the same field, typically account_id, "
                "are computed together in a single query."
            ),
            'examples': _("Ready to copy:"),
            'sample1': "[('account_id.account_type', '=', 'expense')]",
            'sample2': "[('account_id.code', '=like', '60%')]",
            'sample3': "[('account_id', 'in', [1, 2])]",
        }

    # ------------------------------------------------------------------
    # Review
    # ------------------------------------------------------------------
    def _domain_engine_collect_findings(self):
        """ Returns four lists of messages: blocking, intent, slow and informative. """
        self.ensure_one()
        blocking, intent, slow, fine = [], [], [], []
        conditions = self._formula_review_parse(blocking)
        if conditions is None:
            return blocking, intent, slow, fine

        buckets = {'danger': blocking, 'intent': intent, 'warning': slow, 'success': fine}
        for field_expr, _operator, _value in conditions:
            level, message = self._domain_engine_review_condition(field_expr)
            buckets[level].append(message)

        if not conditions:
            intent.append(_(
                "The formula has no condition, so this line adds up every journal item of the "
                "period."
            ))
        elif not blocking:
            self._domain_engine_review_batching(conditions, slow, fine)

        return blocking, intent, slow, fine

    def _domain_engine_review_batching(self, conditions, slow, fine):
        """ Mirror of the batching rule of account.report._compute_formula_batch_with_engine_domain:
        a formula is computed together with others only when every one of its conditions
        starts from the same many2one field of the journal item, and its subformula is not
        count_rows.
        """
        aml_fields = self.env['account.move.line']._fields
        roots = sorted({field_expr.partition('.')[0] for field_expr, _op, _val in conditions})
        subformula = (self.subformula or '').replace('-', '').strip()

        if subformula == 'count_rows':
            slow.append(_(
                "count_rows is always computed with a query of its own, never together with "
                "other lines."
            ))
            return

        root_field = aml_fields.get(roots[0]) if len(roots) == 1 else None
        if root_field is not None and root_field.type == 'many2one':
            if roots[0] == 'account_id':
                fine.append(Markup(_(
                    "Every condition starts from %(field)s, so this line shares a single query "
                    "with every other line built the same way (%(cost)s for all of them)."
                )) % {'field': _code('account_id'), 'cost': COST_AML_BATCH})
            else:
                fine.append(Markup(_(
                    "Every condition starts from %(field)s, so this line shares a single query "
                    "with every other line built only on that field."
                )) % {'field': _code(roots[0])})
            return

        if len(roots) > 1:
            slow.append(Markup(_(
                "The conditions start from several fields (%(fields)s), so this line cannot "
                "share a query with the others and runs one of its own."
            )) % {'fields': Markup(', ').join(_code(r) for r in roots)})
        else:
            slow.append(Markup(_(
                "%(field)s is not a relation to another record, so this line runs a query of "
                "its own instead of sharing one with the others."
            )) % {'field': _code(roots[0])})

    def _domain_engine_review_condition(self, field_expr):
        """ Returns (level, message) for one condition written for the 'domain' engine. """
        self.ensure_one()
        root, _dot, sub_expr = field_expr.partition('.')
        field = self.env['account.move.line']._fields.get(root)

        if field is None:
            if root in self.env['account.analytic.line']._fields:
                return 'danger', Markup(_(
                    "%(field)s is a field of analytic items, not of journal items. To filter "
                    "analytic items, set the engine to Analytic Domain."
                )) % {'field': _code(root)}
            return 'danger', Markup(_(
                "%(field)s does not exist on journal items, so this line would fail."
            )) % {'field': _code(root)}

        if root == 'analytic_distribution':
            return 'intent', Markup(_(
                "%(field)s selects the journal items that carry those analytic accounts, but "
                "each one still counts with its full balance: an expense split 20/30/50 counts "
                "100%% for every one of them (%(cost)s). To add up only the distributed share, "
                "use the Analytic Domain engine."
            )) % {'field': _code(root), 'cost': COST_AML_ANALYTIC}

        if not field.store:
            if getattr(field, 'search', None):
                return 'warning', Markup(_(
                    "%(field)s is not a column: Odoo turns it into a search on each run, whose "
                    "cost depends on how that search is written."
                )) % {'field': _code(field_expr)}
            return 'danger', Markup(_(
                "%(field)s cannot be used in a filter: it is calculated on the fly and Odoo "
                "cannot search it."
            )) % {'field': _code(field_expr)}

        if field.type in ('many2many', 'one2many'):
            return 'warning', Markup(_(
                "%(field)s is a list of records, so it is checked item by item (%(cost)s)."
            )) % {'field': _code(field_expr), 'cost': COST_AML_X2MANY}

        if field.type != 'many2one':
            return 'success', Markup(_(
                "%(field)s is a column of the journal item itself."
            )) % {'field': _code(field_expr)}

        if not sub_expr:
            return 'success', Markup(_(
                "%(field)s is an indexed column of the journal item (%(cost)s)."
            )) % {'field': _code(field_expr), 'cost': COST_AML_COLUMN}

        return self._domain_engine_review_traversal(field_expr, field, sub_expr)

    def _domain_engine_review_traversal(self, field_expr, field, sub_expr):
        """ A condition that walks from the journal item into a related record. """
        comodel = self.env[field.comodel_name]
        sub_field = comodel._fields.get(sub_expr.partition('.')[0])

        if sub_field is None:
            return 'danger', Markup(_(
                "%(field)s does not exist: %(model)s has no field %(sub)s."
            )) % {'field': _code(field_expr), 'model': comodel._description, 'sub': _code(sub_expr)}

        if not sub_field.store and not getattr(sub_field, 'search', None):
            return 'danger', Markup(_(
                "%(field)s cannot be used in a filter: it is calculated on the fly and Odoo "
                "cannot search it."
            )) % {'field': _code(field_expr)}

        if field.comodel_name == 'account.account':
            if not sub_field.store:
                return 'success', Markup(_(
                    "%(field)s is not stored as a column — the account code is kept per company "
                    "— so the chart of accounts is searched for it on each line (%(cost)s)."
                )) % {'field': _code(field_expr), 'cost': COST_AML_ACCOUNT_CODE}
            return 'success', Markup(_(
                "%(field)s reads a column of the accounting account (%(cost)s)."
            )) % {'field': _code(field_expr), 'cost': COST_AML_ACCOUNT_FIELD}

        if field.comodel_name == 'account.move':
            return 'warning', Markup(_(
                "%(field)s reaches the journal entry, which costs a join for every line "
                "(%(cost)s). If the same information exists on the journal item — the journal, "
                "the partner, the date — filter on it there."
            )) % {'field': _code(field_expr), 'cost': COST_AML_MOVE}

        return 'success', Markup(_(
            "%(field)s reads a field of %(model)s through the journal item."
        )) % {'field': _code(field_expr), 'model': comodel._description}
