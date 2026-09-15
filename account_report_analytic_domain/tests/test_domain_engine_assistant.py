from odoo import Command
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestDomainEngineAssistant(TestAccountReportsCommon):
    """ The formula assistant on the native 'Odoo Domain' engine. """

    def _expression(self, formula, subformula='sum'):
        report = self.env['account.report'].create({
            'name': "Domain engine assistant",
            'column_ids': [Command.create({'name': "Balance", 'expression_label': 'balance', 'sequence': 1})],
            'line_ids': [Command.create({
                'name': "Line",
                'expression_ids': [Command.create({
                    'label': 'balance',
                    'engine': 'domain',
                    'formula': formula,
                    'subformula': subformula,
                })],
            })],
        })
        return report.line_ids.expression_ids

    def _review(self, formula, subformula='sum'):
        """ Review a formula the way the form does while it is being typed: on an unsaved
        record. It has to be unsaved, because the native engine refuses to SAVE an invalid
        formula (account.report.expression._check_formula) - which is precisely when the
        assistant is useful, since that error does not say why.
        """
        expression = self.env['account.report.expression'].new({
            'label': 'balance',
            'engine': 'domain',
            'formula': formula,
            'subformula': subformula,
        })
        return expression.analytic_domain_review

    # ------------------------------------------------------------------
    # What works
    # ------------------------------------------------------------------
    def test_account_type_formula_is_fine_and_batched(self):
        review = self._review("[('account_id.account_type', '=', 'expense')]")
        self.assertIn('alert-success', review)
        # Every condition starts from account_id: the native engine batches it.
        self.assertIn('single query', review)

    def test_account_code_explains_the_per_company_code(self):
        review = self._review("[('account_id.code', '=like', '60%')]")
        self.assertIn('alert-success', review)
        self.assertIn('per company', review)

    def test_journal_item_column_is_fine(self):
        review = self._review("[('journal_id', '=', %s)]" % self.company_data['default_journal_misc'].id)
        self.assertIn('alert-success', review)
        self.assertIn('indexed column', review)

    # ------------------------------------------------------------------
    # What will not work
    # ------------------------------------------------------------------
    def test_unknown_field_is_blocking(self):
        review = self._review("[('nonexistent_field', '=', 1)]")
        self.assertIn('alert-danger', review)
        self.assertIn('nonexistent_field', review)

    def test_analytic_item_field_points_at_the_analytic_engine(self):
        """ general_account_id belongs to analytic items: typed on the Odoo Domain engine it
        would fail, and the assistant must say which engine it belongs to.
        """
        review = self._review("[('general_account_id.account_type', '=', 'expense')]")
        self.assertIn('alert-danger', review)
        self.assertIn('Analytic Domain', review)

    def test_unsearchable_account_field_is_blocking(self):
        review = self._review("[('account_id.group_id', '=', 1)]")
        self.assertIn('alert-danger', review)

    def test_invalid_domain_is_blocking(self):
        self.assertIn('alert-danger', self._review("not a domain"))

    # ------------------------------------------------------------------
    # What may not return what the user expects
    # ------------------------------------------------------------------
    def test_analytic_distribution_warns_that_it_does_not_prorate(self):
        """ The mistake this whole module exists for: filtering by analytic distribution on
        journal items brings their full balance, not the distributed share.
        """
        review = self._review("[('analytic_distribution', 'in', [1])]")
        self.assertIn('alert-warning', review)
        self.assertIn('may not return what you expect', review)
        self.assertIn('Analytic Domain', review)
        self.assertIn('100%', review)

    def test_empty_formula_warns_it_takes_everything(self):
        review = self._review("[]")
        self.assertIn('alert-warning', review)
        self.assertIn('every journal item', review)

    # ------------------------------------------------------------------
    # What will be slow
    # ------------------------------------------------------------------
    def test_journal_entry_traversal_is_slow(self):
        review = self._review("[('move_id.move_type', '=', 'out_invoice')]")
        self.assertIn('alert-warning', review)
        self.assertIn('there is a faster way', review)
        self.assertIn('journal entry', review)

    def test_mixed_roots_break_batching(self):
        review = self._review(
            "[('account_id.account_type', '=', 'expense'), ('partner_id', '=', %s)]"
            % self.partner_a.id
        )
        self.assertIn('alert-warning', review)
        self.assertIn('runs one of its own', review)

    def test_x2many_is_slow(self):
        review = self._review("[('tax_tag_ids', 'in', [1])]")
        self.assertIn('alert-warning', review)
        self.assertIn('list of records', review)

    def test_count_rows_is_never_batched(self):
        review = self._review("[('account_id.account_type', '=', 'expense')]", subformula='count_rows')
        self.assertIn('alert-warning', review)
        self.assertIn('count_rows', review)

    # ------------------------------------------------------------------
    # Guide, and the engine itself is untouched
    # ------------------------------------------------------------------
    def test_guide_explains_journal_items_and_the_analytic_alternative(self):
        guide = self.env['account.report.expression'].new({
            'label': 'balance', 'engine': 'domain', 'subformula': 'sum',
            'formula': "[('account_id.account_type', '=', 'expense')]",
        }).analytic_domain_guide
        self.assertIn('alert-info', guide)
        self.assertIn('journal items', guide)
        self.assertIn('analytic_distribution', guide)
        self.assertIn('Analytic Domain', guide)

    def test_native_engine_still_computes(self):
        """ The assistant only reads the formula; the report line keeps its native value. """
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2025-03-15',
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                Command.create({'name': "e", 'account_id': self.company_data['default_account_expense'].id,
                                'debit': 250.0, 'credit': 0.0}),
                Command.create({'name': "c", 'account_id': self.company_data['default_account_payable'].id,
                                'debit': 0.0, 'credit': 250.0}),
            ],
        })
        move.action_post()
        expression = self._expression(
            "[('account_id', '=', %s)]" % self.company_data['default_account_expense'].id
        )
        report = expression.report_line_id.report_id
        options = self._generate_options(report, '2025-01-01', '2025-12-31')
        lines = report._get_lines(options)
        self.assertAlmostEqual(lines[0]['columns'][0]['no_format'], 250.0)
