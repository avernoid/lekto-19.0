from psycopg2 import IntegrityError

from odoo import Command
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestAnalyticDomainEngine(TestAccountReportsCommon):
    """ The scenario is built from scratch on purpose: Odoo.SH loads demo data only
    after running the tests, so anything relying on it would be skipped there.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Not "Departments": Odoo's own analytic demo data ships a plan with that name
        # and every plan adds a same-labelled column to account.analytic.line, which the
        # registry warns about. Caught on Odoo.SH build 37709419.
        cls.analytic_plan = cls.env['account.analytic.plan'].create({'name': "Test cost centres"})
        cls.an_marketing, cls.an_admin, cls.an_management = cls.env['account.analytic.account'].create([
            {'name': "Marketing", 'plan_id': cls.analytic_plan.id},
            {'name': "Administration", 'plan_id': cls.analytic_plan.id},
            {'name': "Management", 'plan_id': cls.analytic_plan.id},
        ])

        cls.expense_account = cls.company_data['default_account_expense']

        # 1000 of expense split 20 Marketing / 30 Administration / 50 Management.
        cls.move = cls._create_distributed_move(
            cls.env.company,
            cls.company_data,
            '2025-03-15',
            1000.0,
            {
                str(cls.an_marketing.id): 20.0,
                str(cls.an_admin.id): 30.0,
                str(cls.an_management.id): 50.0,
            },
        )
        cls.move.action_post()

        cls.report = cls._create_analytic_report(
            "[('auto_account_id', 'in', %s)]" % [cls.an_admin.id, cls.an_management.id],
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @classmethod
    def _create_distributed_move(cls, company, company_data, date, amount, distribution):
        return cls.env['account.move'].with_company(company).create({
            'move_type': 'entry',
            'date': date,
            'journal_id': company_data['default_journal_misc'].id,
            'line_ids': [
                Command.create({
                    'name': "expense",
                    'account_id': company_data['default_account_expense'].id,
                    'debit': amount,
                    'credit': 0.0,
                    'analytic_distribution': distribution,
                }),
                Command.create({
                    'name': "counterpart",
                    'account_id': company_data['default_account_payable'].id,
                    'debit': 0.0,
                    'credit': amount,
                }),
            ],
        })

    @classmethod
    def _create_analytic_report(cls, formula, subformula='sum', groupby=None):
        return cls.env['account.report'].create({
            'name': "Analytic Domain Test Report",
            'filter_date_range': True,
            'filter_show_draft': True,
            'column_ids': [
                Command.create({'name': "Balance", 'expression_label': 'balance', 'sequence': 1}),
            ],
            'line_ids': [
                Command.create({
                    'name': "Administrative expenses",
                    'sequence': 1,
                    'groupby': groupby,
                    'expression_ids': [
                        Command.create({
                            'label': 'balance',
                            'engine': 'analytic_domain',
                            'formula': formula,
                            'subformula': subformula,
                        }),
                    ],
                }),
            ],
        })

    def _line_balance(self, report, date_from='2025-01-01', date_to='2025-12-31', default_options=None):
        options = self._generate_options(report, date_from, date_to, default_options=default_options)
        lines = report._get_lines(options)
        self.assertTrue(lines, "The report should render at least its own line.")
        return lines[0]['columns'][0]['no_format']

    # ------------------------------------------------------------------
    # Core behaviour
    # ------------------------------------------------------------------
    def test_sums_only_the_distributed_share(self):
        """ 30% Administration + 50% Management of a 1000 expense = 800, not 1000. """
        self.assertAlmostEqual(self._line_balance(self.report), 800.0)

    def test_single_analytic_account_share(self):
        report = self._create_analytic_report("[('auto_account_id', '=', %s)]" % self.an_marketing.id)
        self.assertAlmostEqual(self._line_balance(report), 200.0)

    def test_sign_is_accounting_balance(self):
        """ An expense comes out positive, like it does with the 'domain' engine, so that
        analytic lines stay aggregatable with regular ones.
        """
        self.assertGreater(self._line_balance(self.report), 0.0)

    def test_signed_subformula(self):
        """ The subformula is safe_eval'd against the result dict, so '-sum' must work. """
        report = self._create_analytic_report(
            "[('auto_account_id', 'in', %s)]" % [self.an_admin.id, self.an_management.id],
            subformula='-sum',
        )
        self.assertAlmostEqual(self._line_balance(report), -800.0)

    def test_count_rows_subformula(self):
        report = self._create_analytic_report(
            "[('auto_account_id', 'in', %s)]" % [self.an_admin.id, self.an_management.id],
            subformula='count_rows',
        )
        self.assertAlmostEqual(self._line_balance(report), 2.0)

    def test_general_account_domain(self):
        """ The domain may filter on the journal item's account, natively. """
        report = self._create_analytic_report(
            "[('general_account_id.account_type', '=', 'expense'), ('auto_account_id', '=', %s)]" % self.an_admin.id,
        )
        self.assertAlmostEqual(self._line_balance(report), 300.0)

        report_no_match = self._create_analytic_report(
            "[('general_account_id.account_type', '=', 'income'), ('auto_account_id', '=', %s)]" % self.an_admin.id,
        )
        self.assertAlmostEqual(self._line_balance(report_no_match), 0.0)

    # ------------------------------------------------------------------
    # Grouping several analytic accounts without listing them by hand
    # ------------------------------------------------------------------
    def test_sub_plan_groups_several_analytic_accounts(self):
        """ A sub-plan is the native way to categorise analytic accounts: it shares its
        root plan's column, so it groups accounts inside one dimension instead of adding
        a new one, and the domain joins a small table instead of listing ids by hand.
        """
        structure = self.env['account.analytic.plan'].create({
            'name': "Test structure",
            'parent_id': self.analytic_plan.id,
        })
        self.assertEqual(
            structure._column_name(), self.analytic_plan._column_name(),
            "A sub-plan must share its root plan's column, otherwise it would be a "
            "separate analytic dimension rather than a grouping.",
        )

        an_a, an_b = self.env['account.analytic.account'].create([
            {'name': "Sub A", 'plan_id': structure.id},
            {'name': "Sub B", 'plan_id': structure.id},
        ])
        move = self._create_distributed_move(
            self.env.company, self.company_data, '2025-05-10', 500.0,
            {str(an_a.id): 40.0, str(an_b.id): 60.0},
        )
        move.action_post()

        report = self._create_analytic_report(
            "[('%s.plan_id', 'child_of', %s)]" % (self.analytic_plan._column_name(), structure.id),
        )
        # Only the two accounts of the sub-plan, not the ones of the root plan.
        self.assertAlmostEqual(self._line_balance(report), 500.0)

    def test_domain_can_traverse_a_field_of_the_analytic_account(self):
        """ Same idea with any field of the analytic account, a Studio one included:
        the domain traverses the plan column into account.analytic.account.
        """
        (self.an_admin + self.an_management).code = "STRUCT"
        report = self._create_analytic_report(
            "[('%s.code', '=', 'STRUCT')]" % self.analytic_plan._column_name(),
        )
        self.assertAlmostEqual(self._line_balance(report), 800.0)

    # ------------------------------------------------------------------
    # Filtering on the general account
    # ------------------------------------------------------------------
    def test_account_code_prefix(self):
        """ account.account.code is not a column since Odoo 17: it lives in the
        company-dependent code_store jsonb. The engine resolves such conditions to
        account ids once per batch; the result must still be exact.
        """
        self.expense_account.code = 'X9001'
        report = self._create_analytic_report(
            "[('general_account_id.code', '=like', 'X9%%'), ('auto_account_id', 'in', %s)]"
            % [self.an_admin.id, self.an_management.id],
        )
        self.assertAlmostEqual(self._line_balance(report), 800.0)

        no_match = self._create_analytic_report("[('general_account_id.code', '=like', 'ZZ%')]")
        self.assertAlmostEqual(self._line_balance(no_match), 0.0)

    def test_archived_account_is_still_reported(self):
        """ An amount booked on an account archived later still belongs in the report,
        which is why the account resolution runs with active_test=False - the same
        choice the native account_codes engine makes.
        """
        self.expense_account.code = 'X9001'
        report = self._create_analytic_report("[('general_account_id.code', '=like', 'X9%')]")
        self.assertAlmostEqual(self._line_balance(report), 1000.0)

        self.expense_account.active = False
        self.assertAlmostEqual(
            self._line_balance(report), 1000.0,
            "Archiving the account must not silently drop it from the report.",
        )

    def test_account_conditions_cache_does_not_leak_between_formulas(self):
        """ The resolution cache is shared by every formula of the batch: two lines with
        different account conditions must not contaminate each other.
        """
        other_account = self.env['account.account'].create({
            'name': "Other expense",
            'code': 'X9500',
            'account_type': 'expense',
        })
        self.expense_account.code = 'X9001'
        move = self._create_distributed_move(
            self.env.company, self.company_data, '2025-06-10', 300.0, {str(self.an_admin.id): 100.0},
        )
        move.line_ids.filtered(lambda line: line.debit).account_id = other_account
        move.action_post()

        # Two lines sharing the same engine and date scope are computed in one batch, so
        # they share the account resolution cache.
        report = self.env['account.report'].create({
            'name': "Two account conditions",
            'filter_date_range': True,
            'column_ids': [Command.create({'name': "Balance", 'expression_label': 'balance', 'sequence': 1})],
            'line_ids': [
                Command.create({
                    'name': "X9001",
                    'sequence': 1,
                    'expression_ids': [Command.create({
                        'label': 'balance',
                        'engine': 'analytic_domain',
                        'formula': "[('general_account_id.code', '=like', 'X9001%')]",
                        'subformula': 'sum',
                    })],
                }),
                Command.create({
                    'name': "X9500",
                    'sequence': 2,
                    'expression_ids': [Command.create({
                        'label': 'balance',
                        'engine': 'analytic_domain',
                        'formula': "[('general_account_id.code', '=like', 'X9500%')]",
                        'subformula': 'sum',
                    })],
                }),
            ],
        })
        options = self._generate_options(report, '2025-01-01', '2025-12-31')
        lines = report._get_lines(options)
        self.assertAlmostEqual(lines[0]['columns'][0]['no_format'], 1000.0)
        self.assertAlmostEqual(lines[1]['columns'][0]['no_format'], 300.0)

    # ------------------------------------------------------------------
    # Report context: dates and entry state
    # ------------------------------------------------------------------
    def test_dates_of_the_report_are_respected(self):
        """ account.analytic.line.date is the accounting date of the journal item. """
        self.assertAlmostEqual(self._line_balance(self.report, '2025-01-01', '2025-02-28'), 0.0)
        self.assertAlmostEqual(self._line_balance(self.report, '2025-03-01', '2025-03-31'), 800.0)
        self.assertAlmostEqual(self._line_balance(self.report, '2025-04-01', '2025-12-31'), 0.0)

    def test_date_scope_from_beginning(self):
        """ date_scope must widen the range exactly as it does for the 'domain' engine. """
        self.report.line_ids.expression_ids.date_scope = 'from_beginning'
        self.assertAlmostEqual(self._line_balance(self.report, '2025-04-01', '2025-12-31'), 800.0)

    def test_draft_entries_are_excluded(self):
        """ Analytic items are unlinked when a move goes back to draft, so a draft move
        can never contribute to an analytic_domain line.
        """
        self.move.button_draft()
        self.assertFalse(self.move.line_ids.analytic_line_ids)
        self.assertAlmostEqual(self._line_balance(self.report), 0.0)

    def test_cancelled_entries_are_excluded(self):
        self.move.button_cancel()
        self.assertAlmostEqual(self._line_balance(self.report), 0.0)

    def test_all_entries_option_raises_a_warning(self):
        """ 'Include unposted entries' can never widen an analytic line: warn instead of
        silently unbalancing the report against its domain-engine lines.
        """
        options = self._generate_options(self.report, '2025-01-01', '2025-12-31')
        options['all_entries'] = True
        warnings = {}
        self.report._get_lines(options, warnings=warnings)
        self.assertIn(
            'account_report_analytic_domain.analytic_domain_warning_draft_entries',
            warnings,
        )

    def test_analytic_items_without_general_account_are_excluded(self):
        """ Timesheets and manual analytic entries carry no accounting amount. """
        self.env['account.analytic.line'].create({
            'name': "Manual analytic entry",
            'date': '2025-03-15',
            'amount': -5000.0,
            self.analytic_plan._column_name(): self.an_admin.id,
            'company_id': self.env.company.id,
        })
        self.assertAlmostEqual(self._line_balance(self.report), 800.0)

    # ------------------------------------------------------------------
    # Translating the report's own filters
    # ------------------------------------------------------------------
    def _balance_with_forced_domain(self, forced_domain):
        options = self._generate_options(self.report, '2025-01-01', '2025-12-31')
        options['forced_domain'] = forced_domain
        return self.report._get_lines(options)[0]['columns'][0]['no_format']

    def test_account_id_in_a_report_filter_means_the_accounting_account(self):
        """ account.analytic.line has an account_id of its own, but it is the analytic
        account of the project plan. A filter coming from the report speaks of journal
        items, so its account_id is the accounting account and must be renamed - the
        report's own account-type filter is written that way.
        """
        self.assertAlmostEqual(
            self._balance_with_forced_domain([('account_id', '=', self.expense_account.id)]), 800.0,
        )
        self.assertAlmostEqual(
            self._balance_with_forced_domain([
                ('account_id', '=', self.company_data['default_account_payable'].id),
            ]), 0.0,
        )
        self.assertAlmostEqual(
            self._balance_with_forced_domain([('account_id.account_type', '=', 'expense')]), 800.0,
        )

    def test_journal_filter_uses_the_analytic_column(self):
        """ journal_id is a stored related field of the analytic item, so the filter never
        has to travel to the journal item.
        """
        other_journal = self.env['account.journal'].create({
            'name': "Other", 'code': 'OTH', 'type': 'general',
        })
        self.assertAlmostEqual(
            self._balance_with_forced_domain([
                ('journal_id', '=', self.company_data['default_journal_misc'].id),
            ]), 800.0,
        )
        self.assertAlmostEqual(
            self._balance_with_forced_domain([('journal_id', '=', other_journal.id)]), 0.0,
        )

    def test_an_explicit_draft_filter_answers_nothing(self):
        """ The always-true parent_state conditions of the report's own filter are dropped
        as an optimisation, but an explicit request for draft entries must still answer
        nothing rather than everything.
        """
        self.assertAlmostEqual(self._balance_with_forced_domain([('parent_state', '=', 'posted')]), 800.0)
        self.assertAlmostEqual(self._balance_with_forced_domain([('parent_state', '=', 'draft')]), 0.0)

    # ------------------------------------------------------------------
    # Groupby
    # ------------------------------------------------------------------
    def test_groupby_on_analytic_field(self):
        report = self._create_analytic_report(
            "[('auto_account_id', 'in', %s)]" % [self.an_admin.id, self.an_management.id],
            groupby='general_account_id',
        )
        options = self._generate_options(report, '2025-01-01', '2025-12-31')
        options['unfold_all'] = True
        lines = report._get_lines(options)
        self.assertAlmostEqual(lines[0]['columns'][0]['no_format'], 800.0)
        # The line unfolds into a single group, for the one expense account involved.
        self.assertGreater(len(lines), 1)
        self.assertAlmostEqual(lines[1]['columns'][0]['no_format'], 800.0)
        self.assertIn(self.expense_account.display_name, lines[1]['name'])

    def _unfolded(self, report):
        options = self._generate_options(report, '2025-01-01', '2025-12-31')
        options['unfold_all'] = True
        return report._get_lines(options)

    def test_groupby_by_analytic_account(self):
        """ The grouping people actually want: one subline per cost centre. """
        column = self.analytic_plan._column_name()
        report = self._create_analytic_report(
            "[('%s', 'in', [%s, %s])]" % (column, self.an_admin.id, self.an_management.id),
            groupby=column,
        )
        lines = self._unfolded(report)
        self.assertAlmostEqual(lines[0]['columns'][0]['no_format'], 800.0)

        by_name = {line['name']: line['columns'][0]['no_format'] for line in lines[1:]}
        self.assertAlmostEqual(by_name[self.an_admin.display_name], 300.0)
        self.assertAlmostEqual(by_name[self.an_management.display_name], 500.0)
        self.assertNotIn(self.an_marketing.display_name, by_name)

    def test_groupby_by_partner(self):
        partner = self.env['res.partner'].create({'name': "Grouped partner"})
        self.move.button_draft()
        self.move.line_ids.partner_id = partner
        self.move.action_post()

        report = self._create_analytic_report(
            "[('auto_account_id', 'in', %s)]" % [self.an_admin.id, self.an_management.id],
            groupby='partner_id',
        )
        lines = self._unfolded(report)
        self.assertAlmostEqual(lines[0]['columns'][0]['no_format'], 800.0)
        by_name = {line['name']: line['columns'][0]['no_format'] for line in lines[1:]}
        self.assertAlmostEqual(by_name[partner.display_name], 800.0)

    def test_two_level_groupby(self):
        """ Two levels exercise the next_groupby branch, which counts sublines with a
        DISTINCT on the next field rather than with COUNT(*).
        """
        column = self.analytic_plan._column_name()
        report = self._create_analytic_report(
            "[('%s', 'in', [%s, %s])]" % (column, self.an_admin.id, self.an_management.id),
            groupby='general_account_id,%s' % column,
        )
        lines = self._unfolded(report)
        self.assertAlmostEqual(lines[0]['columns'][0]['no_format'], 800.0)

        values = [line['columns'][0]['no_format'] for line in lines[1:]]
        self.assertIn(800.0, values, "The single expense account groups the whole amount.")
        self.assertIn(300.0, values)
        self.assertIn(500.0, values)

    def test_groupby_by_a_field_that_is_not_a_column_is_rejected(self):
        """ auto_account_id can be filtered on but never grouped by: it is computed, so
        there is no column to GROUP BY. The line cannot even be saved, which is the right
        moment to say so - and the message must name the way out.
        """
        with self.assertRaises(UserError) as caught:
            self._create_analytic_report(
                "[('auto_account_id', '=', %s)]" % self.an_admin.id,
                groupby='auto_account_id',
            )
        self.assertIn('analytic plan', str(caught.exception))

    def test_groupby_on_unknown_field_raises(self):
        report = self._create_analytic_report(
            "[('auto_account_id', '=', %s)]" % self.an_admin.id,
            groupby='move_id',  # exists on account.move.line, not on account.analytic.line
        )
        options = self._generate_options(report, '2025-01-01', '2025-12-31')
        options['unfold_all'] = True
        with self.assertRaises(UserError):
            report._get_lines(options)

    # ------------------------------------------------------------------
    # The assistant shown while writing the formula
    # ------------------------------------------------------------------
    def _review(self, formula, subformula='sum'):
        report = self._create_analytic_report(formula, subformula=subformula)
        return report.line_ids.expression_ids.analytic_domain_review

    def test_review_approves_a_sound_formula(self):
        review = self._review(
            "[('%s', 'in', [%s]), ('general_account_id.account_type', '=', 'expense')]"
            % (self.analytic_plan._column_name(), self.an_admin.id)
        )
        self.assertIn('alert-success', review)
        self.assertNotIn('alert-danger', review)

    def test_review_flags_a_field_that_does_not_exist(self):
        review = self._review("[('nonexistent_field', '=', 1)]")
        self.assertIn('alert-danger', review)
        self.assertIn('nonexistent_field', review)

    def test_review_redirects_a_journal_item_field(self):
        """ parent_state exists on the journal item, not on the analytic one: the
        assistant must say so and give the working spelling.
        """
        review = self._review("[('parent_state', '=', 'posted')]")
        self.assertIn('alert-danger', review)
        self.assertIn('move_line_id.parent_state', review)

    def test_review_catches_the_account_id_name_collision(self):
        """ The project plan's column is literally called account_id, so a formula written
        as if it were the accounting account must be caught rather than silently read the
        analytic account.
        """
        project_plan, _other_plans = self.env['account.analytic.plan']._get_all_plans()
        review = self._review(
            "[('%s.account_type', '=', 'expense')]" % project_plan._strict_column_name()
        )
        self.assertIn('alert-danger', review)
        self.assertIn('general_account_id.account_type', review)

    def test_review_warns_about_auto_account_id(self):
        review = self._review("[('auto_account_id', '=', %s)]" % self.an_admin.id)
        self.assertIn('alert-warning', review)
        # It points at the column of a real plan of this database, not at a convention.
        self.assertIn(self.analytic_plan._column_name(), review)

    def test_review_rejects_a_field_odoo_cannot_search(self):
        review = self._review("[('general_account_id.group_id', '!=', False)]")
        self.assertIn('alert-danger', review)

    def test_review_warns_when_no_analytic_account_is_restricted(self):
        review = self._review("[('general_account_id.account_type', '=', 'expense')]")
        self.assertIn('alert-warning', review)

    def test_review_rejects_an_invalid_domain(self):
        self.assertIn('alert-danger', self._review("this is not a domain"))

    def test_review_rejects_an_unknown_subformula(self):
        report = self._create_analytic_report("[('auto_account_id', '=', %s)]" % self.an_admin.id)
        report.line_ids.expression_ids.subformula = 'total'
        self.assertIn('alert-danger', report.line_ids.expression_ids.analytic_domain_review)

    def test_guide_lists_the_real_analytic_plans(self):
        expression = self.report.line_ids.expression_ids
        self.assertIn(self.analytic_plan._column_name(), expression.analytic_domain_guide)
        self.assertIn(self.analytic_plan.display_name, expression.analytic_domain_guide)

    def test_assistant_is_silent_for_other_engines(self):
        report = self.env['account.report'].create({
            'name': "Plain domain report",
            'column_ids': [Command.create({'name': "Balance", 'expression_label': 'balance', 'sequence': 1})],
            'line_ids': [Command.create({
                'name': "Expenses",
                'expression_ids': [Command.create({
                    'label': 'balance',
                    'engine': 'domain',
                    'formula': "[('account_id.account_type', '=', 'expense')]",
                    'subformula': 'sum',
                })],
            })],
        })
        expression = report.line_ids.expression_ids
        self.assertFalse(expression.analytic_domain_review)
        self.assertFalse(expression.analytic_domain_guide)

    # ------------------------------------------------------------------
    # Learning demo
    # ------------------------------------------------------------------
    def test_learning_demo_builds_a_report_that_adds_up(self):
        """ The demo doubles as documentation, so it has to produce the figures it claims.

        It is loaded by the test rather than relied upon: Odoo.SH loads demo data *after*
        running the tests, so anything expecting it to be already there is skipped where
        it matters most.
        """
        self.env['account.report']._load_learning_demo()
        marker = self.env['account.report.line'].search([('code', '=', 'ANDEMO1')], limit=1)
        self.assertTrue(marker, "The demo must create its report.")
        report = marker.report_id

        options = self._generate_options(report, '2025-01-01', '2025-12-31')
        lines = report._get_lines(options)
        by_name = {line['name']: line['columns'][0]['no_format'] for line in lines}

        # The demo posts 1000 + 500, split 20 Marketing / 30 Administración / 50 Gerencia.
        # Only the lines scoped to the demo's own analytic accounts are asserted: the ones
        # filtering by account type also see the entries this test class creates.
        structure = next(v for k, v in by_name.items() if k.startswith('1.'))
        sub_plan = next(v for k, v in by_name.items() if k.startswith('2.'))
        marketing = next(v for k, v in by_name.items() if k.startswith('3.'))
        aggregated = next(v for k, v in by_name.items() if k.startswith('7.'))
        self.assertEqual(len(report.line_ids), 7, "Every lesson line must be created.")

        self.assertAlmostEqual(structure, 1200.0, msg="80% of 1500")
        self.assertAlmostEqual(sub_plan, 1200.0, msg="The sub-plan must match the id list")
        self.assertAlmostEqual(marketing, 300.0, msg="20% of 1500")
        self.assertAlmostEqual(aggregated, 1500.0, msg="An analytic line aggregates like any other")

    def test_learning_demo_is_callable_from_a_function_tag(self):
        """ The demo is loaded by `<function model="account.report" name="..."/>`, and
        odoo.tools.convert only accepts a no-argument call when the method carries the
        _api_model flag — otherwise it does `record_ids, *args = args` on an empty list
        and the whole demo file fails to load.

        The local test database is built without demo data, so that path is never
        exercised here; this pins the requirement instead. Odoo.SH caught it once
        (build 37708633).
        """
        method = type(self.env['account.report'])._load_learning_demo
        self.assertTrue(
            getattr(method, '_api_model', False),
            "_load_learning_demo must be decorated with @api.model to be reachable "
            "from the demo <function> tag.",
        )

    def test_learning_demo_is_idempotent(self):
        self.env['account.report']._load_learning_demo()
        self.env['account.report']._load_learning_demo()
        self.assertEqual(
            self.env['account.report.line'].search_count([('code', '=', 'ANDEMO1')]), 1,
            "Loading the demo twice must not duplicate it, whatever the language.",
        )

    # ------------------------------------------------------------------
    # Configuration guards
    # ------------------------------------------------------------------
    def test_invalid_formula_raises(self):
        report = self._create_analytic_report("this is not a domain")
        with self.assertRaises(UserError):
            self._line_balance(report)

    @mute_logger('odoo.sql_db')
    def test_subformula_is_required(self):
        with self.assertRaises(IntegrityError):
            self._create_analytic_report(
                "[('auto_account_id', '=', %s)]" % self.an_admin.id,
                subformula=False,
            )
            self.env.flush_all()

    def test_engine_is_auditable(self):
        self.assertTrue(self.report.line_ids.expression_ids.auditable)

    def test_audit_cell_opens_analytic_items(self):
        options = self._generate_options(self.report, '2025-01-01', '2025-12-31')
        lines = self.report._get_lines(options)
        expression = self.report.line_ids.expression_ids
        action = self.report.action_audit_cell(options, {
            'report_line_id': self.report.line_ids.id,
            'expression_label': expression.label,
            'column_group_key': list(options['column_groups'].keys())[0],
            'calling_line_dict_id': lines[0]['id'],
        })
        self.assertEqual(action['res_model'], 'account.analytic.line')
        audited = self.env['account.analytic.line'].search(action['domain'])
        self.assertAlmostEqual(sum(-line.amount for line in audited), 800.0)

    # ------------------------------------------------------------------
    # Multi-company / multi-currency
    # ------------------------------------------------------------------
    def test_currency_conversion_matches_the_domain_engine(self):
        """ The currency table must be applied exactly like _currency_table_aml_join does,
        otherwise a consolidated report would mix converted and unconverted amounts.

        Rather than hardcoding a rate, we assert parity: with a 100% distribution, an
        analytic_domain line and a domain line over the same journal items must agree.
        """
        company_2 = self.company_data_2['company']
        analytic_foreign = self.env['account.analytic.account'].create({
            'name': "Foreign administration",
            'plan_id': self.analytic_plan.id,
        })
        move_2 = self._create_distributed_move(
            company_2,
            self.company_data_2,
            '2025-03-15',
            1000.0,
            {str(analytic_foreign.id): 100.0},
        )
        move_2.action_post()

        report = self.env['account.report'].create({
            'name': "Currency parity report",
            'filter_date_range': True,
            'filter_multi_company': 'selector',
            'column_ids': [
                Command.create({'name': "Balance", 'expression_label': 'balance', 'sequence': 1}),
            ],
            'line_ids': [
                Command.create({
                    'name': "Analytic",
                    'sequence': 1,
                    'expression_ids': [Command.create({
                        'label': 'balance',
                        'engine': 'analytic_domain',
                        'formula': "[('auto_account_id', '=', %s)]" % analytic_foreign.id,
                        'subformula': 'sum',
                    })],
                }),
                Command.create({
                    'name': "Accounting",
                    'sequence': 2,
                    'expression_ids': [Command.create({
                        'label': 'balance',
                        'engine': 'domain',
                        'formula': "[('account_id', '=', %s)]" % self.company_data_2['default_account_expense'].id,
                        'subformula': 'sum',
                    })],
                }),
            ],
        })

        report = report.with_context(allowed_company_ids=[self.env.company.id, company_2.id])
        options = self._generate_options(report, '2025-01-01', '2025-12-31')
        lines = report._get_lines(options)

        analytic_value = lines[0]['columns'][0]['no_format']
        accounting_value = lines[1]['columns'][0]['no_format']
        self.assertAlmostEqual(analytic_value, accounting_value)
        self.assertNotAlmostEqual(
            analytic_value, 0.0,
            msg="The scenario must actually produce an amount, otherwise parity is vacuous.",
        )
