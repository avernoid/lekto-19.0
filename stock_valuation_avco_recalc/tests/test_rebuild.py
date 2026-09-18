from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.stock_landed_cost_variance.tests.common import RevaluationCommon


class RebuildMixin:

    def damage(self, move, value):
        """History the engine never saw: a stored exit value written by hand."""
        move.value = value
        self.env.flush_all()

    def rebuild(self, moves, date=None, user=None):
        Wizard = self.env["stock.valuation.recalc.wizard"]
        if user:
            Wizard = Wizard.with_user(user)
        wizard = Wizard.with_context(active_model="stock.move", active_ids=moves.ids).create(
            {"date": date or fields.Date.today()})
        action = wizard.action_confirm_recalc()
        self.env.invalidate_all()
        return self.env["stock.valuation.recalc.audit"].browse(action["res_id"])


@tagged("post_install", "-at_install")
class TestRebuildAverage(RebuildMixin, RevaluationCommon):

    def test_a_damaged_exit_is_brought_back_without_journal_entries(self):
        po = self.purchase(5, 500)
        self.bill(po)
        so = self.sale(3)
        self.invoice(so)
        out = so.picking_ids.move_ids
        self.damage(out, 999.0)
        entries = self.env["account.move"].search_count([])

        audit = self.rebuild(out)

        self.assertAlmostEqual(out.value, 1500.0, 2, "the exit at the engine's cost")
        self.assertKardexInStep()
        self.assertEqual(self.env["account.move"].search_count([]), entries, "a rebuild posts nothing")
        row = self.env["stock.value.variance"].search([("move_id", "=", out.id), ("kind", "=", "recalc")])
        self.assertTrue(row.absorbed)
        self.assertAlmostEqual(row.ledger_amount, -501.0, 2)
        self.assertEqual(audit.mode, "rebuild")
        detail = audit.audit_lines.detail_ids
        self.assertEqual(detail.move_id, out)
        self.assertAlmostEqual(detail.previous_value, 999.0, 2)
        self.assertAlmostEqual(detail.new_value, 1500.0, 2)

    def test_periods_before_the_date_keep_their_values(self):
        self.set_periods()
        po = self.purchase(5, 500, day=self.day(self.p1, 3))
        self.bill(po, day=self.day(self.p1, 3))
        so = self.sale(3, day=self.day(self.p1, 10))
        self.invoice(so, day=self.day(self.p1, 10))
        self.damage(so.picking_ids.move_ids, 999.0)
        filed_p1 = self.known_at(self.p1[1])
        filed_p2 = self.known_at(self.p2[1])

        self.rebuild(so.picking_ids.move_ids, date=self.day(self.p3, 1))

        self.assertAlmostEqual(self.known_at(self.p1[1]), filed_p1, 2)
        self.assertAlmostEqual(self.known_at(self.p2[1]), filed_p2, 2)
        self.assertAlmostEqual(self.known_at(self.p3[1]), self.total_value(), 2)
        events = self.product.with_company(self.company)._variance_events_in_period(*self.p3)
        self.assertEqual([e[1]["kind"] for e in events], ["recalc"], "the difference prints in the rebuild's period")

    def test_a_second_run_changes_nothing(self):
        po = self.purchase(5, 500)
        self.bill(po)
        so = self.sale(3)
        self.damage(so.picking_ids.move_ids, 999.0)
        self.rebuild(so.picking_ids.move_ids)
        audit = self.rebuild(so.picking_ids.move_ids)
        self.assertEqual(audit.audit_lines.moves_affected_count, 0)
        self.assertEqual(self.env["stock.value.variance"].search_count(
            [("move_id", "=", so.picking_ids.move_ids.id), ("kind", "=", "recalc")]), 1)

    def test_value_dropped_on_negative_stock_is_recorded(self):
        engine_env = self.env
        self.env = self.env(context=dict(self.env.context, variance_skip_engine=True))  # history before the engine
        po1 = self.purchase(2, 10)
        self.bill(po1)
        so = self.sale(5)
        po2 = self.purchase(5, 20)
        self.bill(po2)
        self.env = engine_env
        self.assertFalse(self.env["stock.value.variance"].search([("product_id", "=", self.product.id)]))
        self.rebuild(so.picking_ids.move_ids)
        live = self.env["stock.value.variance"].search([("product_id", "=", self.product.id),
                                                         ("kind", "=", "negative_stock")])
        self.assertAlmostEqual(sum(live.mapped("ledger_amount")), -30.0, 2, "measured discard of the scenario")
        self.assertKardexInStep()

    def test_a_locked_period_cannot_receive_the_rebuild(self):
        self.set_periods()
        self.company.fiscalyear_lock_date = self.p2[1]
        po = self.purchase(1, 10)
        with self.assertRaises(ValidationError):
            self.rebuild(po.picking_ids.move_ids, date=self.day(self.p2, 5))

    def test_the_wizard_runs_for_a_stock_manager(self):
        """ACLs apply: the audit is born in a single create because nobody may write it."""
        manager = self.env["res.users"].create({
            "name": "Rebuild Manager", "login": "rebuild_manager",
            "group_ids": [(6, 0, [self.env.ref("stock.group_stock_manager").id,
                                  self.env.ref("account.group_account_manager").id])],
            "company_ids": [(6, 0, self.company.ids)], "company_id": self.company.id,
        })
        po = self.purchase(5, 500)
        so = self.sale(3)
        self.damage(so.picking_ids.move_ids, 999.0)
        audit = self.rebuild(so.picking_ids.move_ids, user=manager)
        self.assertEqual(audit.audit_lines.moves_affected_count, 1)
        self.assertTrue(po)

    def test_audit_trail_cannot_be_edited_or_deleted(self):
        access = self.env["ir.model.access"].search([("model_id.model", "in", (
            "stock.valuation.recalc.audit", "stock.valuation.recalc.audit.line",
            "stock.valuation.recalc.audit.detail"))])
        self.assertTrue(access)
        for rule in access:
            self.assertFalse(rule.perm_write, f"{rule.name} grants write on the audit trail")
            self.assertFalse(rule.perm_unlink, f"{rule.name} grants unlink on the audit trail")


@tagged("post_install", "-at_install")
class TestRebuildFifo(RebuildMixin, RevaluationCommon):
    COST_METHOD = "fifo"

    def test_fifo_exit_is_brought_back(self):
        po = self.purchase(5, 10)
        self.bill(po)
        po2 = self.purchase(5, 20)
        self.bill(po2)
        so = self.sale(7)
        self.damage(so.picking_ids.move_ids, 1.0)
        self.rebuild(so.picking_ids.move_ids)
        self.assertAlmostEqual(so.picking_ids.move_ids.value, 90.0, 2, "5 x 10 + 2 x 20")
        self.assertKardexInStep()
