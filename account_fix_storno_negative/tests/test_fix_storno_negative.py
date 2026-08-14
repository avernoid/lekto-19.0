from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestFixStornoNegative(AccountTestInvoicingCommon):
    """Reproduce un asiento tipo storno (débito/crédito negativos) y verifica
    que la acción lo reexpresa a la forma estándar sin tocar el balance."""

    def _make_storno_move(self):
        recv = self.company_data['default_account_receivable']
        inc = self.company_data['default_account_revenue']
        # is_storno=True fuerza que _compute_debit_credit meta el valor negativo
        # en la columna "natural", exactamente como el bug del cliente.
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'is_storno': True,
            'line_ids': [
                Command.create({'account_id': recv.id, 'balance': -100.0}),
                Command.create({'account_id': inc.id, 'balance': 100.0}),
            ],
        })
        move.action_post()
        return move, recv, inc

    def test_negatives_moved_to_opposite_column_positive(self):
        move, recv, inc = self._make_storno_move()
        recv_line = move.line_ids.filtered(lambda l: l.account_id == recv)
        inc_line = move.line_ids.filtered(lambda l: l.account_id == inc)

        # Estado inicial: representación storno (negativos).
        self.assertEqual(recv_line.debit, -100.0)
        self.assertEqual(recv_line.credit, 0.0)
        self.assertEqual(inc_line.debit, 0.0)
        self.assertEqual(inc_line.credit, -100.0)
        self.assertTrue(move.is_storno)

        move.action_fix_storno_negative()

        # El valor saltó a la columna opuesta y salió positivo, derivando la
        # columna estándar desde balance: recv (balance -100) -> crédito 100;
        # inc (balance +100) -> débito 100.
        self.assertEqual(recv_line.debit, 0.0)
        self.assertEqual(recv_line.credit, 100.0)
        self.assertEqual(inc_line.debit, 100.0)
        self.assertEqual(inc_line.credit, 0.0)
        # is_storno apagado para que no revierta en un recálculo futuro.
        self.assertFalse(move.is_storno)
        # balance intacto -> conciliación / EDI / totales sin cambios.
        self.assertEqual(recv_line.balance, -100.0)
        self.assertEqual(inc_line.balance, 100.0)
        # el asiento sigue cuadrado en la representación estándar.
        self.assertEqual(sum(move.line_ids.mapped('debit')), 100.0)
        self.assertEqual(sum(move.line_ids.mapped('credit')), 100.0)

    def test_only_negative_lines_are_touched(self):
        # Un asiento estándar (sin negativos) no debe alterarse y la acción
        # debe avisar que no había nada que corregir.
        recv = self.company_data['default_account_receivable']
        inc = self.company_data['default_account_revenue']
        clean = self.env['account.move'].create({
            'move_type': 'entry',
            'line_ids': [
                Command.create({'account_id': recv.id, 'balance': 100.0}),
                Command.create({'account_id': inc.id, 'balance': -100.0}),
            ],
        })
        clean.action_post()
        before = clean.line_ids.mapped(lambda l: (l.debit, l.credit))

        result = clean.action_fix_storno_negative()

        self.assertEqual(clean.line_ids.mapped(lambda l: (l.debit, l.credit)), before)
        self.assertEqual(result['params']['type'], 'warning')

    def _make_clean_move(self):
        recv = self.company_data['default_account_receivable']
        inc = self.company_data['default_account_revenue']
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'line_ids': [
                Command.create({'account_id': recv.id, 'balance': 100.0}),
                Command.create({'account_id': inc.id, 'balance': -100.0}),
            ],
        })
        move.action_post()
        return move

    def test_wizard_excludes_moves_without_negatives(self):
        # Selección mixta: uno con negativos + uno sano. El sano no se cuenta
        # ni se corrige; solo se informa como ignorado.
        storno, _recv, _inc = self._make_storno_move()
        clean = self._make_clean_move()
        selection = storno | clean
        clean_before = clean.line_ids.mapped(lambda l: (l.debit, l.credit))

        act = selection.action_open_fix_storno_wizard()
        wizard = self.env['account.fix.storno.wizard'].browse(act['res_id'])

        # Solo el asiento con negativos cuenta; el otro va a "ignorados".
        self.assertEqual(wizard.move_count, 1)
        self.assertEqual(wizard.line_count, 2)
        self.assertEqual(wizard.skipped_count, 1)

        wizard.action_confirm()

        # El sano quedó intacto; el storno se corrigió.
        self.assertEqual(clean.line_ids.mapped(lambda l: (l.debit, l.credit)), clean_before)
        self.assertFalse(storno.is_storno)
        self.assertFalse(storno.line_ids.filtered(lambda l: l.debit < 0 or l.credit < 0))

    def test_wizard_nothing_to_correct(self):
        # Selección sin negativos: 0 a corregir, todos ignorados.
        clean = self._make_clean_move()
        act = clean.action_open_fix_storno_wizard()
        wizard = self.env['account.fix.storno.wizard'].browse(act['res_id'])
        self.assertEqual(wizard.move_count, 0)
        self.assertEqual(wizard.line_count, 0)
        self.assertEqual(wizard.skipped_count, 1)

    def test_reconciliation_survives_the_fix(self):
        # Concilia una línea normal (balance +100) contra una línea storno
        # (balance -100, debit=-100) en la cuenta por cobrar, y verifica que
        # tras el fix la conciliación sigue intacta.
        recv = self.company_data['default_account_receivable']
        inc = self.company_data['default_account_revenue']

        normal = self.env['account.move'].create({
            'move_type': 'entry',
            'line_ids': [
                Command.create({'account_id': recv.id, 'balance': 100.0}),
                Command.create({'account_id': inc.id, 'balance': -100.0}),
            ],
        })
        normal.action_post()

        storno = self.env['account.move'].create({
            'move_type': 'entry',
            'is_storno': True,
            'line_ids': [
                Command.create({'account_id': recv.id, 'balance': -100.0}),
                Command.create({'account_id': inc.id, 'balance': 100.0}),
            ],
        })
        storno.action_post()

        normal_recv = normal.line_ids.filtered(lambda l: l.account_id == recv)
        storno_recv = storno.line_ids.filtered(lambda l: l.account_id == recv)

        # Estado storno de partida.
        self.assertEqual(storno_recv.debit, -100.0)
        self.assertEqual(storno_recv.credit, 0.0)

        # Conciliar ambas líneas por cobrar -> conciliación total.
        (normal_recv | storno_recv).reconcile()
        self.assertTrue(normal_recv.reconciled)
        self.assertTrue(storno_recv.reconciled)
        self.assertTrue(storno_recv.full_reconcile_id)

        full_rec_before = storno_recv.full_reconcile_id
        partials_before = storno_recv.matched_debit_ids | storno_recv.matched_credit_ids

        # Aplicar el fix sobre el asiento storno (ya conciliado).
        storno.action_fix_storno_negative()

        # La representación quedó estándar...
        self.assertEqual(storno_recv.debit, 0.0)
        self.assertEqual(storno_recv.credit, 100.0)
        self.assertFalse(storno.is_storno)
        # ...y la conciliación sobrevive intacta.
        self.assertTrue(storno_recv.reconciled)
        self.assertTrue(normal_recv.reconciled)
        self.assertEqual(storno_recv.amount_residual, 0.0)
        self.assertEqual(normal_recv.amount_residual, 0.0)
        self.assertEqual(storno_recv.full_reconcile_id, full_rec_before)
        self.assertEqual(
            storno_recv.matched_debit_ids | storno_recv.matched_credit_ids,
            partials_before,
        )
        # balance intacto en ambas líneas.
        self.assertEqual(storno_recv.balance, -100.0)
        self.assertEqual(normal_recv.balance, 100.0)
