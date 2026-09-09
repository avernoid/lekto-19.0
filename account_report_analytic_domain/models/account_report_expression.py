from ast import literal_eval

from markupsafe import Markup

from odoo import _, api, fields, models

ANALYTIC_DOMAIN_SUBFORMULAS = ('sum', 'sum_if_pos', 'sum_if_neg', 'count_rows')

# Reference timings, measured with EXPLAIN (ANALYZE) on a production database of
# 218k journal items / 43k analytic items / 7.6k accounts. They are shown to the user
# as orders of magnitude, not as promises.
COST_PLAN_COLUMN = "~2 ms"
COST_ACCOUNT_TRAVERSAL = "~3 ms"
COST_ACCOUNT_CODE = "~5 ms"
COST_AUTO_ACCOUNT = "~16 ms"
COST_MOVE_LINE = "~58 ms"


def _code(text):
    """ A field name, styled, with its content escaped. """
    return Markup('<code>%s</code>') % text


class AccountReportExpression(models.Model):
    _inherit = 'account.report.expression'

    engine = fields.Selection(
        selection_add=[('analytic_domain', "Analytic Domain")],
        ondelete={'analytic_domain': 'cascade'},
    )

    analytic_domain_guide = fields.Html(
        string="How to write it",
        compute='_compute_analytic_domain_guide',
        sanitize=False,
        help="Shown only for the Analytic Domain engine. Lists the analytic plans of this "
             "database with the field name each one answers to, since that name depends on "
             "the plan's database id and cannot be guessed, and offers formulas ready to "
             "copy. It is computed while the form is open and costs nothing when the report "
             "is run.",
    )
    analytic_domain_review = fields.Html(
        string="Formula review",
        compute='_compute_analytic_domain_review',
        sanitize=False,
        help="Shown only for the Analytic Domain engine. Reads the formula as it is typed "
             "and reports what would not work (a field that does not exist on analytic "
             "items, one that Odoo cannot search, an invalid domain or subformula) "
             "separately from what would merely be slow, with the measured cost of each way "
             "of writing the filter. It is advisory: it never blocks saving.",
    )

    _analytic_domain_engine_subformula_required = models.Constraint(
        "CHECK(engine != 'analytic_domain' OR subformula IS NOT NULL)",
        "Expressions using 'analytic_domain' engine should all have a subformula.",
    )

    def _get_auditable_engines(self):
        # The formula already is an account.analytic.line domain, so auditing a cell
        # only needs to open that domain in the analytic items view.
        return super()._get_auditable_engines() | {'analytic_domain'}

    # ------------------------------------------------------------------
    # Assistance shown while the formula is being written
    # ------------------------------------------------------------------
    @api.model
    def _analytic_domain_plan_columns(self):
        """ {column name: plan name} for every root analytic plan of this database.

        Nobody can guess that the plan named "Departments" is the column x_plan6_id, so
        the assistant spells it out instead of documenting a convention.
        """
        project_plan, other_plans = self.env['account.analytic.plan']._get_all_plans()
        return {
            plan._strict_column_name(): plan.display_name
            for plan in (project_plan + other_plans)
        }

    @api.depends('engine')
    def _compute_analytic_domain_guide(self):
        for expression in self:
            if expression.engine != 'analytic_domain':
                expression.analytic_domain_guide = False
                continue

            plan_columns = self._analytic_domain_plan_columns()
            sample_column = next(iter(plan_columns), 'account_id')

            plans_html = Markup().join(
                Markup('<li>%s — %s</li>') % (_code(column), name)
                for column, name in plan_columns.items()
            ) or Markup('<li>%s</li>') % _("No analytic plan is defined yet.")

            expression.analytic_domain_guide = Markup(
                '<div class="alert alert-info mb-0" role="status">'
                '<p class="mb-2"><b>%(title)s</b> %(intro)s</p>'
                '<p class="mb-1">%(plans_intro)s</p>'
                '<ul class="mb-2">%(plans)s</ul>'
                '<p class="mb-1">%(fields_intro)s</p>'
                '<ul class="mb-2">'
                '<li>%(c_account)s — %(account)s</li>'
                '<li>%(c_natives)s — %(natives)s</li>'
                '<li>%(c_move_line)s — %(move_line)s</li>'
                '</ul>'
                '<p class="mb-1">%(examples)s</p>'
                '<pre class="mb-0">%(sample1)s\n%(sample2)s\n%(sample3)s</pre>'
                '</div>'
            ) % {
                'title': _("This formula filters analytic items, not journal items."),
                'intro': _(
                    "Each one already carries its share of the journal item's balance, so the "
                    "report line only adds them up. Subformula: sum, -sum, sum_if_pos, "
                    "sum_if_neg or count_rows."
                ),
                'plans_intro': _("To filter by analytic account, use the column of its plan:"),
                'plans': plans_html,
                'fields_intro': _("Other useful fields:"),
                'c_account': _code('general_account_id'),
                'account': _("the accounting account. You may filter its type, code or tags."),
                'c_natives': Markup(', ').join(
                    _code(name) for name in ('date', 'partner_id', 'product_id')
                ),
                'natives': _("available directly on the analytic item."),
                'c_move_line': _code('move_line_id.<field>'),
                'move_line': _("anything that only exists on the journal item. Slow, avoid when you can."),
                'examples': _("Ready to copy:"),
                'sample1': f"[('{sample_column}', 'in', [1, 2])]",
                'sample2': f"[('{sample_column}.plan_id', 'child_of', 3)]",
                'sample3': (
                    f"[('{sample_column}', 'in', [1, 2]), "
                    "('general_account_id.account_type', '=', 'expense')]"
                ),
            }

    @api.depends('engine', 'formula', 'subformula')
    def _compute_analytic_domain_review(self):
        for expression in self:
            if expression.engine != 'analytic_domain':
                expression.analytic_domain_review = False
                continue
            expression.analytic_domain_review = expression._analytic_domain_render_review()

    def _analytic_domain_render_review(self):
        """ Static analysis of the formula: what will not work first, what will be slow
        second. The two are never merged into one indicator, because a broken condition
        matters more than a slow one and would be hidden by it.
        """
        self.ensure_one()
        blocking, slow, fine = self._analytic_domain_collect_findings()

        if blocking:
            level, headline = 'danger', _("This formula will not work")
        elif slow:
            level, headline = 'warning', _("This formula works, but there is a faster way")
        else:
            level, headline = 'success', _("This formula is fine")

        return Markup(
            '<div class="alert alert-%(level)s mb-0" role="status">'
            '<p class="mb-1"><b>%(headline)s</b></p>'
            '<ul class="mb-0">%(items)s</ul>'
            '</div>'
        ) % {
            'level': Markup(level),
            'headline': headline,
            'items': Markup().join(
                Markup('<li>%s</li>') % message for message in (blocking + slow + fine)
            ),
        }

    def _analytic_domain_collect_findings(self):
        """ Returns three lists of messages: blocking, slow and merely informative. """
        self.ensure_one()
        blocking, slow, fine = [], [], []

        subformula = (self.subformula or '').replace('-', '').strip()
        if not subformula:
            blocking.append(_(
                "A subformula is required: sum, -sum, sum_if_pos, sum_if_neg or count_rows."
            ))
        elif subformula not in ANALYTIC_DOMAIN_SUBFORMULAS:
            blocking.append(Markup(_(
                "%(subformula)s is not a valid subformula. Use sum, -sum, sum_if_pos, "
                "sum_if_neg or count_rows."
            )) % {'subformula': _code(self.subformula)})

        try:
            domain = literal_eval(self.formula or '[]')
            conditions = [term for term in domain if isinstance(term, (tuple, list)) and len(term) == 3]
        except (ValueError, SyntaxError, TypeError):
            blocking.append(_("The formula is not a valid Odoo domain."))
            return blocking, slow, fine

        plan_columns = self._analytic_domain_plan_columns()
        narrows_analytic_account = False

        for condition in conditions:
            field_expr = condition[0]
            if not isinstance(field_expr, str):
                continue
            root = field_expr.partition('.')[0]
            if root in plan_columns or root == 'auto_account_id':
                narrows_analytic_account = True
            level, message = self._analytic_domain_review_condition(field_expr, plan_columns)
            {'danger': blocking, 'warning': slow, 'success': fine}[level].append(message)

        if conditions and not narrows_analytic_account:
            slow.append(_(
                "No condition restricts the analytic account, so this line adds up every "
                "analytic item matching the rest of the filter. That is allowed, but make "
                "sure it is what you mean."
            ))

        return blocking, slow, fine

    def _analytic_domain_review_condition(self, field_expr, plan_columns):
        """ Returns (level, message) for a single condition of the domain. """
        self.ensure_one()
        root, _dot, sub_expr = field_expr.partition('.')

        if root in plan_columns:
            return self._analytic_domain_review_plan_condition(field_expr, root, sub_expr, plan_columns)

        if root == 'auto_account_id':
            return 'warning', Markup(_(
                "%(field)s means “the analytic account of any plan”, so every plan is searched "
                "at once and no index can be used (%(cost)s against %(fast)s). Prefer the column "
                "of the plan you actually mean: %(columns)s."
            )) % {
                'field': _code('auto_account_id'),
                'cost': COST_AUTO_ACCOUNT,
                'fast': COST_PLAN_COLUMN,
                'columns': Markup(', ').join(_code(column) for column in plan_columns) or _("none defined"),
            }

        if root == 'move_line_id':
            return 'warning', Markup(_(
                "%(field)s reaches the journal item, a table far larger than the analytic one "
                "(%(cost)s against %(fast)s). Use it only for something that exists nowhere "
                "else: the journal, the partner and the product are already on the analytic "
                "item itself."
            )) % {'field': _code(field_expr), 'cost': COST_MOVE_LINE, 'fast': COST_PLAN_COLUMN}

        if root == 'general_account_id':
            return self._analytic_domain_review_account_condition(field_expr, sub_expr)

        if root in self.env['account.analytic.line']._fields:
            return 'success', Markup(_(
                "%(field)s is a field of the analytic item itself, so it costs nothing extra."
            )) % {'field': _code(field_expr)}

        if root in self.env['account.move.line']._fields:
            return 'danger', Markup(_(
                "%(field)s does not exist on analytic items: it belongs to the journal item. "
                "Write %(suggestion)s instead, bearing in mind it is slower (%(cost)s)."
            )) % {
                'field': _code(root),
                'suggestion': _code(f'move_line_id.{field_expr}'),
                'cost': COST_MOVE_LINE,
            }

        return 'danger', Markup(_(
            "%(field)s does not exist on analytic items, so this line would fail."
        )) % {'field': _code(root)}

    def _analytic_domain_review_plan_condition(self, field_expr, root, sub_expr, plan_columns):
        """ Conditions on an analytic plan column, including the trap of its name.

        The project plan's column is literally called account_id, so somebody used to the
        Odoo Domain engine writes account_id.account_type meaning the accounting account
        and silently reads the analytic one instead.
        """
        plan = plan_columns[root]
        if sub_expr:
            sub_root = sub_expr.partition('.')[0]
            if sub_root not in self.env['account.analytic.account']._fields:
                if sub_root in self.env['account.account']._fields:
                    return 'danger', Markup(_(
                        "%(field)s reads the analytic account of plan “%(plan)s”, not the "
                        "accounting account — they are different things that happen to share "
                        "a field name. For the accounting account write %(suggestion)s."
                    )) % {
                        'field': _code(field_expr),
                        'plan': plan,
                        'suggestion': _code(f'general_account_id.{sub_expr}'),
                    }
                return 'danger', Markup(_(
                    "%(field)s does not exist on the analytic account."
                )) % {'field': _code(field_expr)}

            return 'success', Markup(_(
                "%(field)s reads a field of the analytic account of plan “%(plan)s”. Grouping "
                "accounts this way is the fastest option (%(cost)s) and beats listing their "
                "ids by hand."
            )) % {'field': _code(field_expr), 'plan': plan, 'cost': COST_PLAN_COLUMN}

        return 'success', Markup(_(
            "%(field)s — analytic account of plan “%(plan)s”. This is the fastest way to "
            "filter (%(cost)s): it uses the index of that column."
        )) % {'field': _code(field_expr), 'plan': plan, 'cost': COST_PLAN_COLUMN}

    def _analytic_domain_review_account_condition(self, field_expr, sub_expr):
        """ Conditions reaching account.account: some of its fields are not columns. """
        if not sub_expr:
            return 'success', Markup(_(
                "%(field)s is an indexed column of the analytic item (%(cost)s)."
            )) % {'field': _code('general_account_id'), 'cost': COST_ACCOUNT_TRAVERSAL}

        sub_field = self.env['account.account']._fields.get(sub_expr.partition('.')[0])
        if sub_field is None:
            return 'danger', Markup(_(
                "%(field)s does not exist on the accounting account."
            )) % {'field': _code(field_expr)}

        if sub_field.store:
            return 'success', Markup(_(
                "%(field)s reads a real column of the accounting account, and the chart of "
                "accounts is small, so it is cheap (%(cost)s)."
            )) % {'field': _code(field_expr), 'cost': COST_ACCOUNT_TRAVERSAL}

        if getattr(sub_field, 'search', None):
            return 'success', Markup(_(
                "%(field)s is not stored as a column — the account code is kept per company — "
                "so it is resolved to a list of accounts once for the whole report (%(cost)s). "
                "Accounts archived later are still included."
            )) % {'field': _code(field_expr), 'cost': COST_ACCOUNT_CODE}

        return 'danger', Markup(_(
            "%(field)s cannot be used in a filter: it is calculated on the fly and Odoo cannot "
            "search it. Filter by account code or by account tag instead."
        )) % {'field': _code(field_expr)}
