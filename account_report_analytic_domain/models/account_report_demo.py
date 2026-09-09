from odoo import _, api, models

# The demo is recognised by the code of its first line, never by its name: the name is
# translated when it is created, so searching for it would break in any other language.
DEMO_MARKER_CODE = "ANDEMO1"


class AccountReport(models.Model):
    _inherit = 'account.report'

    # ------------------------------------------------------------------
    # Learning demo
    # ------------------------------------------------------------------
    @api.model
    def _load_learning_demo(self):
        """ Build a small but complete scenario that shows what the engine is for.

        It is written in Python rather than in XML for one hard reason: the field that
        holds an analytic account on an analytic item is the *column of its plan*, whose
        name depends on the plan's database id (`x_plan6_id`). It cannot be written down
        in advance, only asked for at load time.

        The report is meant to be read as a lesson: each line demonstrates one way of
        writing the formula, and its name says which. Opening any of them shows the
        assistant, which explains and rates that particular formula.

        @api.model is required, not decorative: a <function> tag with no arguments makes
        odoo.tools.convert do `record_ids, *args = args` unless the method carries the
        _api_model flag, which fails on an empty argument list.
        """
        if self.env['account.report.line'].search_count([('code', '=', DEMO_MARKER_CODE)]):
            return  # already loaded

        company = self.env.company
        accounts = self._analytic_demo_create_analytic_accounts()
        expense_account = self._analytic_demo_expense_account(company)

        if expense_account:
            self._analytic_demo_create_moves(company, expense_account, accounts)

        self._analytic_demo_create_report(accounts, expense_account)

    def _analytic_demo_create_analytic_accounts(self):
        """ One root plan with two sub-plans, so both ways of grouping can be shown.

        The name matters: every analytic plan adds a column to account.analytic.line
        labelled after it, and Odoo warns when two columns share a label. Its own demo
        data already ships plans called Project, Departments and Internal, so ours must
        not be one of those.
        """
        plan = self.env['account.analytic.plan'].create({'name': _("Cost Centres")})
        structure, commercial = self.env['account.analytic.plan'].create([
            {'name': _("Structure"), 'parent_id': plan.id},
            {'name': _("Commercial"), 'parent_id': plan.id},
        ])
        administration, management, marketing = self.env['account.analytic.account'].create([
            {'name': _("Administration"), 'plan_id': structure.id},
            {'name': _("Management"), 'plan_id': structure.id},
            {'name': _("Marketing"), 'plan_id': commercial.id},
        ])
        return {
            'plan': plan,
            'structure': structure,
            'commercial': commercial,
            'administration': administration,
            'management': management,
            'marketing': marketing,
        }

    def _analytic_demo_expense_account(self, company):
        return self.env['account.account'].search([
            ('account_type', '=', 'expense'),
            ('company_ids', 'in', company.id),
        ], limit=1)

    def _analytic_demo_create_moves(self, company, expense_account, accounts):
        """ Two entries, in two different months, so the date filter has something to do.

        The first one is the textbook case: a single 1 000 expense split three ways. No
        report line built on journal items can show 800 of it; that is the whole point.
        """
        journal = self.env['account.journal'].search([
            ('type', '=', 'general'), ('company_id', '=', company.id),
        ], limit=1)
        payable = self.env['account.account'].search([
            ('account_type', '=', 'liability_payable'),
            ('company_ids', 'in', company.id),
        ], limit=1)
        if not journal or not payable:
            return

        distribution = {
            str(accounts['marketing'].id): 20.0,
            str(accounts['administration'].id): 30.0,
            str(accounts['management'].id): 50.0,
        }
        moves = self.env['account.move'].create([
            self._analytic_demo_move_values(journal, expense_account, payable, date, amount, distribution)
            for date, amount in (('2025-03-15', 1000.0), ('2025-06-10', 500.0))
        ])
        moves.action_post()

    def _analytic_demo_move_values(self, journal, expense_account, payable, date, amount, distribution):
        return {
            'move_type': 'entry',
            'date': date,
            'ref': _("Expense split 20 Marketing / 30 Administration / 50 Management"),
            'journal_id': journal.id,
            'line_ids': [
                (0, 0, {
                    'name': _("Distributed expense"),
                    'account_id': expense_account.id,
                    'debit': amount,
                    'credit': 0.0,
                    'analytic_distribution': distribution,
                }),
                (0, 0, {
                    'name': _("Counterpart"),
                    'account_id': payable.id,
                    'debit': 0.0,
                    'credit': amount,
                }),
            ],
        }

    def _analytic_demo_create_report(self, accounts, expense_account):
        """ One line per way of writing the formula, named after what it teaches. """
        column = accounts['plan']._column_name()
        structure_ids = [accounts['administration'].id, accounts['management'].id]
        code_prefix = (expense_account.code or '')[:2] if expense_account else ''

        lines = [
            (
                _("1. Administration + Management — through the plan's column (the fastest way)"),
                'analytic_domain',
                "[('%s', 'in', %s)]" % (column, structure_ids),
                'sum',
            ),
            (
                _("2. The same, without listing accounts — through the sub-plan Structure"),
                'analytic_domain',
                "[('%s.plan_id', 'child_of', %s)]" % (column, accounts['structure'].id),
                'sum',
            ),
            (
                _("3. Marketing — a single analytic account"),
                'analytic_domain',
                "[('%s', '=', %s)]" % (column, accounts['marketing'].id),
                'sum',
            ),
            (
                _("4. All the expense, by accounting account type"),
                'analytic_domain',
                "[('general_account_id.account_type', '=', 'expense')]",
                'sum',
            ),
        ]
        if code_prefix:
            lines.append((
                _("5. All the expense, by accounting account prefix %s", code_prefix),
                'analytic_domain',
                "[('general_account_id.code', '=like', '%s%%')]" % code_prefix,
                'sum',
            ))

        line_commands = [
            (0, 0, {
                'name': name,
                'sequence': sequence,
                'code': 'ANDEMO%s' % sequence,
                'expression_ids': [(0, 0, {
                    'label': 'balance',
                    'engine': engine,
                    'formula': formula,
                    'subformula': subformula,
                })],
            })
            for sequence, (name, engine, formula, subformula) in enumerate(lines, start=1)
        ]

        # Grouped line: the same total, unfolded by accounting account.
        line_commands.append((0, 0, {
            'name': _("6. Structure expense, unfoldable by accounting account"),
            'sequence': len(line_commands) + 1,
            'groupby': 'general_account_id',
            'expression_ids': [(0, 0, {
                'label': 'balance',
                'engine': 'analytic_domain',
                'formula': "[('%s', 'in', %s)]" % (column, structure_ids),
                'subformula': 'sum',
            })],
        }))

        # Aggregation: proves an analytic line adds up with the rest of the report.
        line_commands.append((0, 0, {
            'name': _("7. Sum of 1 + 3 — an analytic line aggregates like any other"),
            'sequence': len(line_commands) + 1,
            'expression_ids': [(0, 0, {
                'label': 'balance',
                'engine': 'aggregation',
                'formula': 'ANDEMO1.balance + ANDEMO3.balance',
            })],
        }))

        return self.env['account.report'].create({
            'name': _("Expenses by cost centre (analytic)"),
            'filter_date_range': True,
            'filter_multi_company': 'selector',
            'column_ids': [(0, 0, {
                'name': _("Balance"),
                'expression_label': 'balance',
                'sequence': 1,
                'figure_type': 'monetary',
            })],
            'line_ids': line_commands,
        })
