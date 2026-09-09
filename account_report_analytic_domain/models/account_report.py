from ast import literal_eval
from collections import defaultdict

from odoo import _, api, models
from odoo.addons.web.controllers.utils import clean_action
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import SQL, Query


class AccountReport(models.Model):
    _inherit = 'account.report'

    ####################################################
    # ENGINE: analytic_domain
    ####################################################
    def _compute_formula_batch_with_engine_analytic_domain(
        self, options, date_scope, formulas_dict, current_groupby, next_groupby,
        offset=0, limit=None, warnings=None,
    ):
        """ Report engine.

        Formulas made for this engine consist of a domain on account.analytic.line;
        only those analytic items will be used to compute the result. It is the exact
        counterpart of the 'domain' engine, which works on account.move.line.

        No analytic distribution has to be applied here: account.analytic.line.amount
        already holds the share of the journal item's balance that was distributed to
        that analytic account. Its sign is the opposite of the accounting balance
        (see account.move.line._prepare_analytic_distribution_line), so this engine
        sums -amount, keeping its results consistent with, and aggregatable with, the
        results of the other engines.

        This engine supports the same subformulas as the 'domain' engine:
        - sum: the result will be the sum of the matched analytic items' balances
        - sum_if_pos: the same as sum only if it's positive; else 0
        - sum_if_neg: the same as sum only if it's negative; else 0
        - count_rows: the number of sublines this expression has

        As for every other engine, the subformula is evaluated against the result
        dict, so it may be signed (e.g. '-sum').
        """
        self._analytic_domain_check_groupby_fields(
            (next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else [])
        )

        if warnings is not None and options.get('all_entries'):
            # Analytic items only exist for posted entries: account.move.button_draft
            # unlinks them, and button_cancel resets to draft first. Including unposted
            # entries can therefore never widen an analytic_domain line, which would
            # silently unbalance it against the domain-engine lines of the same report.
            warnings['account_report_analytic_domain.analytic_domain_warning_draft_entries'] = {'alert_type': 'warning'}

        rslt = {}
        # Shared by every formula of the batch: resolving a condition on a non-stored
        # field of account.account costs a sequential scan of the whole chart, and a
        # report has many lines. See _analytic_domain_resolve_account_conditions.
        account_conditions_cache = {}

        for formula, expressions in formulas_dict.items():
            try:
                formula_domain = Domain(literal_eval(formula))
            except (ValueError, SyntaxError):
                raise UserError(_(
                    'Invalid analytic domain formula in expression "%(expression)s" of line "%(line)s": %(formula)s',
                    expression=expressions[0].label,
                    line=expressions[0].report_line_id.name,
                    formula=formula,
                ))

            formula_domain = self._analytic_domain_resolve_account_conditions(
                formula_domain, account_conditions_cache,
            )
            query_res_lines = self._analytic_domain_execute_query(
                options, date_scope, formula_domain, current_groupby, next_groupby, offset, limit,
            )

            formula_rslt = []
            total_sum = 0.0
            for query_res in query_res_lines:
                totals = {
                    'sum': query_res['sum'],
                    'sum_if_pos': 0,
                    'sum_if_neg': 0,
                    'count_rows': query_res['count_rows'],
                    'has_sublines': bool(query_res['count_rows']),
                }
                total_sum += query_res['sum']
                formula_rslt.append((query_res.get('grouping_key'), totals))

            rslt.update(self._analytic_domain_split_by_sign_policy(
                formula, expressions, formula_rslt, total_sum, current_groupby,
            ))

        return rslt

    def _analytic_domain_split_by_sign_policy(self, formula, expressions, formula_rslt, total_sum, current_groupby):
        """ Apply the sum_if_pos/sum_if_neg subformulas the way the 'domain' engine does:
        the sign policy is decided on the total of the line, not row by row, so that a
        grouped line stays consistent with its own total.
        """
        def format_result(rslt_rows):
            if current_groupby:
                return rslt_rows
            if rslt_rows:
                return rslt_rows[0][1]
            return {'sum': 0, 'sum_if_pos': 0, 'sum_if_neg': 0, 'count_rows': 0, 'has_sublines': False}

        expressions_by_sign_policy = defaultdict(lambda: self.env['account.report.expression'])
        for expression in expressions:
            subformula_without_sign = (expression.subformula or '').replace('-', '').strip()
            if subformula_without_sign in ('sum_if_pos', 'sum_if_neg'):
                expressions_by_sign_policy[subformula_without_sign] += expression
            else:
                expressions_by_sign_policy['no_sign_check'] += expression

        rslt = {}
        if expressions_by_sign_policy['sum_if_pos'] or expressions_by_sign_policy['sum_if_neg']:
            # >= instead of > is intended, mirroring the 'domain' engine: 0 counts as positive.
            sign_policy_with_value = (
                'sum_if_pos'
                if self.env.company.currency_id.compare_amounts(total_sum, 0.0) >= 0
                else 'sum_if_neg'
            )
            formula_rslt_with_sign = [
                (grouping_key, {**totals, sign_policy_with_value: totals['sum']})
                for grouping_key, totals in formula_rslt
            ]
            for sign_policy in ('sum_if_pos', 'sum_if_neg'):
                policy_expressions = expressions_by_sign_policy[sign_policy]
                if policy_expressions:
                    matching = sign_policy == sign_policy_with_value
                    rslt[formula, policy_expressions] = format_result(formula_rslt_with_sign if matching else [])

        if expressions_by_sign_policy['no_sign_check']:
            rslt[formula, expressions_by_sign_policy['no_sign_check']] = format_result(formula_rslt)

        return rslt

    def _analytic_domain_execute_query(
        self, options, date_scope, formula_domain, current_groupby, next_groupby, offset, limit,
    ):
        """ Run the aggregation query for the analytic_domain engine and return its raw rows. """
        self.ensure_one()
        analytic_line = self.env['account.analytic.line']
        domain = self._get_analytic_domain_options_domain(options, date_scope) & formula_domain
        search_query = analytic_line._search(domain)

        groupby_sql = (
            analytic_line._field_to_sql('account_analytic_line', current_groupby, search_query)
            if current_groupby else None
        )
        if next_groupby:
            count_select = SQL("COUNT(DISTINCT %s)", analytic_line._field_to_sql(
                'account_analytic_line', next_groupby.split(',')[0], search_query,
            ))
        else:
            # The 'domain' engine counts DISTINCT id here. id being the primary key that
            # is exactly COUNT(*), but asking for the DISTINCT makes PostgreSQL sort the
            # rows and, worse, drives it to scan by primary key instead of the selective
            # partial indexes of account_analytic_line. Measured 60ms -> 16ms on a
            # production database.
            count_select = SQL("COUNT(*)")

        sql_query = SQL(
            """
            SELECT
                COALESCE(SUM(%(balance_select)s), 0.0) AS sum,
                %(count_select)s AS count_rows
                %(select_groupby_sql)s
            FROM %(table_references)s
            %(currency_table_join)s
            WHERE %(search_condition)s
            %(groupby_sql)s
            %(order_by_sql)s
            %(tail_query)s
            """,
            # account.analytic.line.amount is the opposite of the accounting balance.
            balance_select=self._currency_table_apply_rate(SQL("-account_analytic_line.amount")),
            count_select=count_select,
            select_groupby_sql=SQL(', %s AS grouping_key', groupby_sql) if groupby_sql else SQL(),
            table_references=search_query.from_clause,
            currency_table_join=self._currency_table_analytic_line_join(options),
            search_condition=search_query.where_clause or SQL("TRUE"),
            groupby_sql=SQL('GROUP BY %s', groupby_sql) if groupby_sql else SQL(),
            order_by_sql=SQL(' ORDER BY %s', groupby_sql) if groupby_sql else SQL(),
            tail_query=self._get_engine_query_tail(offset, limit),
        )
        self.env.cr.execute(sql_query)
        return self.env.cr.dictfetchall()

    ####################################################
    # OPTIONS -> account.analytic.line domain
    ####################################################
    def _get_analytic_domain_options_domain(self, options, date_scope) -> Domain:
        """ Counterpart of _get_options_domain for account.analytic.line: turns the
        report's own filters into a domain the analytic items can be searched with.
        """
        self.ensure_one()

        # Translating the report's whole journal-item domain, rather than picking the
        # filters we think matter, is what keeps this engine honest: a filter added by
        # another module is honoured instead of silently ignored.
        domain = self._analytic_domain_through_move_line(self._get_options_domain(options, date_scope))

        # Analytic items with no general account (timesheets, manually encoded analytic
        # entries) carry no accounting amount. Odoo excludes them from its own analytic
        # shadowing query and so do we, to never mix hours into a monetary report line.
        return domain & Domain('general_account_id', '!=', False)

    def _analytic_domain_resolve_account_conditions(self, domain: Domain, cache: dict) -> Domain:
        """ Pre-resolve conditions that reach a **non-stored** field of account.account
        into a plain list of account ids, shared by the whole batch of formulas.

        `code` is the one that matters: since Odoo 17 it is not a column but a
        company-dependent value inside the `code_store` jsonb, so a prefix condition
        costs a sequential scan of the entire chart of accounts. Every report line paid
        for its own scan; resolving once took a measured line from 31 ms to 5 ms on a
        7 600-account chart.

        This mirrors what the native account_codes engine does — it resolves all accounts
        once per batch too — except it resolves them in SQL rather than by reading a
        computed field record by record in Python.

        Stored fields (account_type, reconcile...) are left alone: the ORM already emits
        an indexed JOIN for them, which is better than materialising ids.

        Archived accounts are kept, like the account_codes engine does: an amount booked
        on an account that was archived later still belongs in the report.
        """
        if domain.is_true() or domain.is_false():
            return domain

        account_fields = self.env['account.account']._fields

        def resolve(condition):
            root, _dot, sub_expr = condition.field_expr.partition('.')
            if root != 'general_account_id' or not sub_expr:
                return condition

            sub_field = account_fields.get(sub_expr.partition('.')[0])
            if sub_field is None or sub_field.store:
                return condition

            key = (sub_expr, condition.operator, repr(condition.value))
            if key not in cache:
                cache[key] = self.env['account.account'].with_context(active_test=False).search(
                    Domain(sub_expr, condition.operator, condition.value)
                ).ids
            return Domain('general_account_id', 'in', cache[key])

        return domain.map_conditions(resolve)

    @api.model
    def _analytic_domain_through_move_line(self, domain: Domain) -> Domain:
        """ Rewrite a journal-item domain into an analytic-item one, condition by
        condition rather than per source: forced_domain carries both the report's own
        filters, expressed in journal-item fields, and the sub-domains _expand_groupby
        injects when unfolding, which are already analytic fields.

        Three rules, in order:

        1. `account_id` is renamed to `general_account_id`. This one is not optional:
           account.analytic.line HAS an account_id, but it is the analytic account of the
           project plan, not the accounting account. Left alone, the report's account-type
           filter would silently read the wrong column.
        2. The two always-true `parent_state` conditions the report's own "include unposted
           entries" filter produces are dropped: analytic items exist only for posted
           entries, so they would only buy a join into account_move_line. Any other
           `parent_state` condition is translated normally — asking for draft entries must
           answer nothing, not everything.
        3. A field that exists on the analytic item is kept (date, company_id, partner_id,
           journal_id — a stored related field — product_id...); anything else is reached
           through move_line_id.
        """
        if domain.is_true() or domain.is_false():
            return domain

        analytic_fields = self.env['account.analytic.line']._fields

        def through_move_line(condition):
            field_expr = condition.field_expr
            root, dot, sub_expr = field_expr.partition('.')

            if root == 'account_id':
                field_expr = 'general_account_id' + dot + sub_expr
                return Domain(field_expr, condition.operator, condition.value)

            if (field_expr, condition.operator, condition.value) in (
                ('parent_state', '=', 'posted'),
                ('parent_state', '!=', 'cancel'),
            ):
                return Domain.TRUE

            if root in analytic_fields:
                return condition

            return Domain(f'move_line_id.{field_expr}', condition.operator, condition.value)

        return domain.map_conditions(through_move_line)

    ####################################################
    # CURRENCY TABLE
    ####################################################
    @api.model
    def _currency_table_analytic_line_join(self, options) -> SQL:
        """ Counterpart of _currency_table_aml_join for account.analytic.line.

        Same conversion rules as for journal items; the only difference is that the
        general account is reached through general_account_id instead of account_id.
        """
        if options['currency_table']['type'] == 'cta':
            return SQL(
                """
                    JOIN account_account aal_ct_account
                        ON aal_ct_account.id = account_analytic_line.general_account_id
                    LEFT JOIN %(currency_table)s
                        ON account_analytic_line.company_id = account_currency_table.company_id
                        AND (
                            account_currency_table.rate_type = CASE
                                WHEN aal_ct_account.account_type LIKE ANY (ARRAY[%(income_prefix)s, %(expense_prefix)s, 'equity_unaffected']) THEN 'average'
                                WHEN aal_ct_account.account_type LIKE %(equity_prefix)s THEN 'historical'
                                ELSE 'current'
                            END
                        )
                        AND (account_currency_table.date_from IS NULL OR account_currency_table.date_from <= account_analytic_line.date)
                        AND (account_currency_table.date_next IS NULL OR account_currency_table.date_next > account_analytic_line.date)
                        AND (account_currency_table.period_key = %(period_key)s OR account_currency_table.period_key IS NULL)
                """,
                equity_prefix='equity%',
                income_prefix='income%',
                expense_prefix='expense%',
                currency_table=self._get_currency_table(options),
                period_key=options['date']['currency_table_period_key'],
            )

        return SQL(
            """
                JOIN %(currency_table)s
                    ON account_analytic_line.company_id = account_currency_table.company_id
                    AND (account_currency_table.period_key = %(period_key)s OR account_currency_table.period_key IS NULL)
            """,
            currency_table=self._get_currency_table(options),
            period_key=options['date']['currency_table_period_key'],
        )

    ####################################################
    # GROUPBY
    ####################################################
    def _check_groupby_fields(self, groupby_fields_name):
        """ account.report.line._validate_groupby validates every groupby against
        account.move.line, which would forbid saving a line grouped by an analytic-only
        field such as general_account_id.

        The engine of the line cannot be consulted here: creating a whole report in a
        single call validates its lines before their expressions exist. So we accept a
        groupby that is valid on account.analytic.line, and the analytic_domain engine
        checks it again, strictly, when the line is actually rendered.
        """
        try:
            return super()._check_groupby_fields(groupby_fields_name)
        except UserError:
            self._analytic_domain_check_groupby_fields(groupby_fields_name)

    def _analytic_domain_check_groupby_fields(self, groupby_fields_name):
        """ Same checks as _check_groupby_fields, but against account.analytic.line. """
        self.ensure_one()
        analytic_line = self.env['account.analytic.line']

        if isinstance(groupby_fields_name, str | bool):
            groupby_fields_name = groupby_fields_name.split(',') if groupby_fields_name else []

        for field_name in (fname.strip() for fname in groupby_fields_name if fname):
            groupby_field = analytic_line._fields.get(field_name)
            if not groupby_field:
                raise UserError(_(
                    "Field %s does not exist on account.analytic.line and can therefore not be used in a groupby "
                    "of an expression using the 'Analytic Domain' engine.", field_name,
                ))
            if not groupby_field._description_searchable:
                raise UserError(_(
                    "Field %s of account.analytic.line is not searchable and can therefore not be used in a groupby "
                    "expression.", field_name,
                ))
            try:
                # A searchable field is not necessarily a column: auto_account_id, for
                # instance, is computed and can be filtered on but never grouped by.
                analytic_line._field_to_sql(
                    'account_analytic_line', field_name, Query(self.env, 'account_analytic_line'),
                )
            except ValueError:
                raise UserError(_(
                    "Field %s of account.analytic.line cannot be used in a groupby expression, because it is not "
                    "stored in the database. Group by the column of an analytic plan instead.", field_name,
                ))

    ####################################################
    # AUDIT
    ####################################################
    def action_audit_cell(self, options, params):
        report_line = self.env['account.report.line'].browse(params['report_line_id'])
        expression = report_line.expression_ids.filtered(lambda x: x.label == params['expression_label'])

        if expression.engine != 'analytic_domain':
            return super().action_audit_cell(options, params)

        column_group_options = self._get_column_group_options(options, params['column_group_key'])
        domain = self._get_analytic_domain_options_domain(column_group_options, expression.date_scope)
        # Resolved the same way the engine does, or an archived account would be counted
        # in the total and missing from the items the audit shows.
        domain &= self._analytic_domain_resolve_account_conditions(Domain(literal_eval(expression.formula)), {})
        domain &= Domain(self._get_audit_line_groupby_domain(params['calling_line_dict_id']))

        action = clean_action(
            self.env.ref('analytic.account_analytic_line_action_entries')._get_action_dict(), env=self.env,
        )
        action['domain'] = list(domain)
        return action
