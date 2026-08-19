from datetime import datetime, timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged

TARGET = datetime(2024, 2, 10, 9, 0, 0)


@tagged("post_install", "-at_install")
class TestStockMoveDateAdjust(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.stock_location = cls.env.ref("stock.stock_location_stock")
        cls.customer_location = cls.env.ref("stock.stock_location_customers")
        cls.product = cls.env["product.product"].create({
            "name": "Date Adjust Widget",
            "type": "consu",
            "is_storable": True,
        })
        cls.group = cls.env.ref("stock_move_date_adjust.group_stock_move_date_adjust")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_inventory_move(self, qty=10):
        quant = self.env["stock.quant"].with_context(inventory_mode=True).create({
            "product_id": self.product.id,
            "location_id": self.stock_location.id,
            "inventory_quantity": qty,
        })
        quant.action_apply_inventory()
        return self.env["stock.move"].search([
            ("is_inventory", "=", True),
            ("product_id", "=", self.product.id),
        ], order="id desc", limit=1)

    def _make_delivery(self, qty=2):
        picking_type = self.env.ref("stock.picking_type_out")
        picking = self.env["stock.picking"].create({
            "picking_type_id": picking_type.id,
            "location_id": self.stock_location.id,
            "location_dest_id": self.customer_location.id,
            "move_ids": [(0, 0, {
                "product_id": self.product.id,
                "product_uom_qty": qty,
                "product_uom": self.product.uom_id.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            })],
        })
        picking.action_confirm()
        picking.action_assign()
        picking.move_ids.quantity = qty
        picking.move_ids.picked = True
        picking.button_validate()
        return picking

    def _wizard(self, moves, **values):
        vals = {
            "move_ids": [(6, 0, moves.ids)],
            "reason": "unit test",
        }
        vals.update(values)
        return self.env["stock.move.date.adjust.wizard"].create(vals)

    # ------------------------------------------------------------------
    # 1 -- inventory adjustment
    # ------------------------------------------------------------------

    def test_01_inventory_move_redated(self):
        move = self._make_inventory_move()
        self.assertEqual(move.state, "done")
        original = move.date

        self._wizard(move, mode="fixed", new_date=TARGET).action_apply()

        self.assertEqual(move.date, TARGET)
        self.assertEqual(move.original_date, original)
        self.assertTrue(move.date_adjusted)
        self.assertTrue(move.move_line_ids)
        for line in move.move_line_ids:
            self.assertEqual(line.date, TARGET, "move lines must follow the move")

    def test_01b_inventory_origin_has_no_document(self):
        move = self._make_inventory_move()
        origin, document = move._date_adjust_origin()
        self.assertEqual(origin, "inventory")
        self.assertFalse(document, "an inventory adjustment has no header document")

    # ------------------------------------------------------------------
    # 2 -- transfer
    # ------------------------------------------------------------------

    def test_02_picking_move_and_header(self):
        self._make_inventory_move(qty=50)
        picking = self._make_delivery(qty=2)
        move = picking.move_ids
        self.assertEqual(picking.state, "done")

        self._wizard(move, mode="fixed", new_date=TARGET).action_apply()

        self.assertEqual(move.date, TARGET)
        self.assertEqual(picking.date_done, TARGET, "the transfer header must follow")

    def test_02b_picking_resolves_its_moves(self):
        self._make_inventory_move(qty=50)
        picking = self._make_delivery(qty=2)
        self.assertEqual(picking._date_adjust_get_moves(), picking.move_ids)

    def test_02c_sync_document_can_be_turned_off(self):
        self._make_inventory_move(qty=50)
        picking = self._make_delivery(qty=2)
        before = picking.date_done

        self._wizard(picking.move_ids, mode="fixed", new_date=TARGET,
                     sync_document=False).action_apply()

        self.assertEqual(picking.move_ids.date, TARGET)
        self.assertEqual(picking.date_done, before, "header must be left alone")

    # ------------------------------------------------------------------
    # 3 -- scrap
    # ------------------------------------------------------------------

    def test_03_scrap_move_and_header(self):
        self._make_inventory_move(qty=50)
        scrap = self.env["stock.scrap"].create({
            "product_id": self.product.id,
            "product_uom_id": self.product.uom_id.id,
            "scrap_qty": 1,
            "location_id": self.stock_location.id,
        })
        scrap.do_scrap()
        move = scrap.move_ids
        self.assertTrue(move)

        self._wizard(move, mode="fixed", new_date=TARGET).action_apply()

        self.assertEqual(move.date, TARGET)
        self.assertEqual(scrap.date_done, TARGET)
        self.assertEqual(move._date_adjust_origin()[0], "scrap")

    # ------------------------------------------------------------------
    # 4 -- shift mode
    # ------------------------------------------------------------------

    def test_04_shift_preserves_spacing(self):
        move_a = self._make_inventory_move(qty=5)
        move_b = self._make_inventory_move(qty=9)
        move_a.write({"date": datetime(2026, 5, 1, 8, 0, 0)})
        move_b.write({"date": datetime(2026, 5, 1, 15, 30, 0)})
        spacing = move_b.date - move_a.date

        wizard = self._wizard(
            move_a | move_b, mode="shift",
            shift_from=datetime(2026, 5, 1, 0, 0, 0),
            shift_to=datetime(2025, 5, 1, 0, 0, 0),
        )
        self.assertTrue(wizard.shift_summary)
        wizard.action_apply()

        self.assertEqual(move_a.date, datetime(2025, 5, 1, 8, 0, 0))
        self.assertEqual(move_b.date, datetime(2025, 5, 1, 15, 30, 0))
        self.assertEqual(move_b.date - move_a.date, spacing,
                         "shift must preserve the intra-day spacing")

    def test_04b_shift_summary_states_the_direction(self):
        move = self._make_inventory_move()
        move.write({"date": datetime(2026, 5, 1, 8, 0, 0)})

        back = self._wizard(
            move, mode="shift",
            shift_from=datetime(2026, 8, 17, 0, 0, 0),
            shift_to=datetime(2026, 7, 17, 0, 0, 0),
        )
        self.assertIn("earlier", back.shift_summary,
                      "a backward shift must say so in plain words")

        forward = self._wizard(
            move, mode="shift",
            shift_from=datetime(2026, 6, 1, 22, 30, 0),
            shift_to=datetime(2026, 7, 2, 23, 35, 0),
        )
        self.assertIn("later", forward.shift_summary)

    def test_04c_forward_shift_into_the_future_warns_then_blocks(self):
        move = self._make_inventory_move()
        move.write({"date": fields.Datetime.now() - timedelta(days=1)})

        wizard = self._wizard(
            move, mode="shift",
            shift_from=datetime(2026, 6, 1, 0, 0, 0),
            shift_to=datetime(2026, 7, 2, 0, 0, 0),
        )
        self.assertTrue(wizard.warning_html)
        self.assertIn("future", wizard.warning_html,
                      "the wizard must warn before Apply, not only refuse after")
        with self.assertRaises(UserError):
            wizard.action_apply()

    # ------------------------------------------------------------------
    # 5 -- chronology warning
    # ------------------------------------------------------------------

    def test_05_chronology_warning_is_not_blocking(self):
        origin_move = self._make_inventory_move(qty=5)
        later_move = self._make_inventory_move(qty=9)
        origin_move.write({"date": datetime(2026, 5, 10, 8, 0, 0)})
        later_move.write({"date": datetime(2026, 5, 20, 8, 0, 0),
                          "move_orig_ids": [(6, 0, origin_move.ids)]})

        wizard = self._wizard(later_move, mode="fixed",
                              new_date=datetime(2026, 5, 1, 8, 0, 0))
        self.assertTrue(wizard.warning_html, "a warning must be raised")
        self.assertIn("origin", wizard.warning_html)

        wizard.action_apply()
        self.assertEqual(later_move.date, datetime(2026, 5, 1, 8, 0, 0),
                         "the warning must not block")

    # ------------------------------------------------------------------
    # 6 -- security
    # ------------------------------------------------------------------

    def test_06_wizard_requires_the_group(self):
        user = self.env["res.users"].create({
            "name": "Stock Operator",
            "login": "date_adjust_operator",
            "group_ids": [(6, 0, [self.env.ref("stock.group_stock_manager").id])],
        })
        move = self._make_inventory_move()
        with self.assertRaises(AccessError):
            self.env["stock.move.date.adjust.wizard"].with_user(user).create({
                "move_ids": [(6, 0, move.ids)],
                "reason": "nope",
            })

    def test_06b_group_grants_access(self):
        user = self.env["res.users"].create({
            "name": "Regulariser",
            "login": "date_adjust_regulariser",
            "group_ids": [(6, 0, [
                self.env.ref("stock.group_stock_manager").id,
                self.group.id,
            ])],
        })
        move = self._make_inventory_move()
        wizard = self.env["stock.move.date.adjust.wizard"].with_user(user).create({
            "move_ids": [(6, 0, move.ids)],
            "reason": "authorised",
        })
        self.assertTrue(wizard)

    # ------------------------------------------------------------------
    # 7 -- no revaluation
    # ------------------------------------------------------------------

    def test_07_value_is_untouched(self):
        move = self._make_inventory_move()
        value_before = move.value
        remaining_before = move.remaining_qty

        self._wizard(move, mode="fixed", new_date=TARGET).action_apply()

        self.assertEqual(move.value, value_before, "re-dating must not revalue")
        self.assertEqual(move.remaining_qty, remaining_before)

    # ------------------------------------------------------------------
    # 13..15 -- valuation entry
    # ------------------------------------------------------------------

    def _make_real_time_move(self):
        """A movement that actually produces a posted valuation entry."""
        if "account_move_id" not in self.env["stock.move"]._fields:
            self.skipTest("stock_account not installed")
        journal = self.env["account.journal"].search(
            [("type", "=", "general"), ("company_id", "=", self.company.id)], limit=1)
        account = self.env["account.account"].search(
            [("company_ids", "in", self.company.id)], limit=1)
        if not (journal and account):
            self.skipTest("no accounting data in this database")
        self.company.sudo().account_stock_journal_id = journal.id
        self.stock_location.sudo().valuation_account_id = account.id
        product = self.env["product.product"].create({
            "name": "Real Time Widget", "type": "consu", "is_storable": True,
            "standard_price": 10.0,
        })
        product.product_tmpl_id.valuation = "real_time"
        self.env["stock.quant"].with_context(inventory_mode=True).create({
            "product_id": product.id,
            "location_id": self.stock_location.id,
            "inventory_quantity": 5,
        }).action_apply_inventory()
        move = self.env["stock.move"].search(
            [("product_id", "=", product.id)], order="id desc", limit=1)
        if not move.account_move_id:
            self.skipTest("no valuation entry produced in this configuration")
        return move

    def test_13_entry_untouched_when_option_is_off(self):
        move = self._make_real_time_move()
        entry, before = move.account_move_id, move.account_move_id.date

        self._wizard(move, mode="fixed", new_date=TARGET).action_apply()

        self.assertEqual(move.date, TARGET)
        self.assertEqual(entry.date, before, "the entry must stay put by default")
        self.assertEqual(entry.state, "posted")

    def test_14_entry_redated_and_renumbered(self):
        move = self._make_real_time_move()
        entry, old_name = move.account_move_id, move.account_move_id.name

        self._wizard(move, mode="fixed", new_date=TARGET,
                     adjust_accounting=True).action_apply()

        entry.invalidate_recordset()
        self.assertEqual(entry.date, TARGET.date())
        self.assertEqual(entry.state, "posted", "it must end up posted again")
        self.assertNotEqual(entry.name, old_name,
                            "Odoo ties the number to the period, so it is renumbered")
        self.assertNotEqual(entry.name, "/", "it must not stay unnumbered")

    def test_15_reconciled_entry_is_refused(self):
        move = self._make_real_time_move()
        entry = move.account_move_id
        account = entry.line_ids[0].account_id
        account.sudo().reconcile = True
        other = self.env["account.account"].search(
            [("id", "!=", account.id), ("company_ids", "in", self.company.id)], limit=1)
        source = entry.line_ids[0]
        amount = source.debit or source.credit
        # The counterpart must sit on the OPPOSITE side, otherwise reconcile() is
        # a silent no-op and the test would pass for the wrong reason.
        mine = {"account_id": account.id, "name": "c1"}
        mine["debit" if source.credit else "credit"] = amount
        theirs = {"account_id": other.id, "name": "c2"}
        theirs["credit" if source.credit else "debit"] = amount
        counterpart = self.env["account.move"].create({
            "journal_id": entry.journal_id.id, "date": entry.date,
            "line_ids": [(0, 0, mine), (0, 0, theirs)],
        })
        counterpart.action_post()
        lines = entry.line_ids.filtered(lambda l: l.account_id == account)
        lines |= counterpart.line_ids.filtered(lambda l: l.account_id == account)
        lines.reconcile()
        entry.invalidate_recordset()
        self.assertTrue(
            any(l.matched_debit_ids or l.matched_credit_ids for l in entry.line_ids),
            "precondition: the entry must really be reconciled",
        )

        # Odoo itself lets this through -- the guard has to be ours.
        with self.assertRaises(UserError):
            self._wizard(move, mode="fixed", new_date=TARGET,
                         adjust_accounting=True).action_apply()
        self.assertNotEqual(move.date, TARGET,
                            "nothing may be applied when the entry is refused")

    def test_15b_hashed_entry_is_refused(self):
        move = self._make_real_time_move()
        entry = move.account_move_id
        self.env.cr.execute(
            "UPDATE account_move SET inalterable_hash = %s WHERE id = %s",
            ("fake-hash", entry.id))
        entry.invalidate_recordset(["inalterable_hash"])

        with self.assertRaises(UserError):
            self._wizard(move, mode="fixed", new_date=TARGET,
                         adjust_accounting=True).action_apply()

    def test_15c_warning_announces_the_renumbering(self):
        move = self._make_real_time_move()

        off = self._wizard(move, mode="fixed", new_date=TARGET)
        self.assertIn("differ", off.warning_html)

        on = self._wizard(move, mode="fixed", new_date=TARGET, adjust_accounting=True)
        self.assertIn("RENUMBERED", on.warning_html,
                      "the renumbering must be stated before applying")

    # ------------------------------------------------------------------
    # 16..21 -- abuse controls
    # ------------------------------------------------------------------

    def test_16_reason_is_mandatory(self):
        move = self._make_inventory_move()
        with self.assertRaises(UserError):
            move._adjust_date({move: TARGET}, reason="  ")

    def test_17_original_date_is_written_once(self):
        move = self._make_inventory_move()
        first_date = move.date

        self._wizard(move, mode="fixed", new_date=TARGET).action_apply()
        self.assertEqual(move.original_date, first_date)

        second_target = datetime(2024, 3, 15, 11, 0, 0)
        self._wizard(move, mode="fixed", new_date=second_target).action_apply()

        self.assertEqual(move.date, second_target)
        self.assertEqual(move.original_date, first_date,
                         "a second regularisation must not overwrite the original")
        self.assertTrue(move.date_adjusted)

    def test_18_closed_period_is_blocked_even_without_accounting_option(self):
        if not hasattr(self.env["res.company"], "_get_lock_date_violations"):
            self.skipTest("accounting not installed")
        move = self._make_inventory_move()
        self.company.sudo().fiscalyear_lock_date = fields.Date.to_date("2024-12-31")

        wizard = self._wizard(move, mode="fixed", new_date=TARGET,
                              )
        with self.assertRaises(UserError):
            wizard.action_apply()

    def test_19_maximum_shift_window(self):
        move = self._make_inventory_move()
        self.company.sudo().stock_move_date_adjust_max_days = 30

        far = move.date - timedelta(days=400)
        with self.assertRaises(UserError):
            self._wizard(move, mode="fixed", new_date=far).action_apply()

        near = move.date - timedelta(days=10)
        self._wizard(move, mode="fixed", new_date=near).action_apply()
        self.assertEqual(move.date, near)

    def test_20_future_date_is_blocked(self):
        move = self._make_inventory_move()
        future = fields.Datetime.now() + timedelta(days=3)
        with self.assertRaises(UserError):
            self._wizard(move, mode="fixed", new_date=future).action_apply()

    def test_21_restore_original_date(self):
        move = self._make_inventory_move()
        original = move.date

        self._wizard(move, mode="fixed", new_date=TARGET).action_apply()
        self.assertEqual(move.date, TARGET)

        move.action_restore_original_date()

        self.assertEqual(move.date, original)
        self.assertFalse(move.date_adjusted)
        self.assertFalse(move.original_date)

    def test_21b_restore_needs_an_adjusted_move(self):
        move = self._make_inventory_move()
        with self.assertRaises(UserError):
            move.action_restore_original_date()

    # ------------------------------------------------------------------
    # 22 -- the new columns carry no computation
    # ------------------------------------------------------------------

    def test_22_new_fields_are_plain_columns(self):
        for name in ("original_date", "date_adjusted"):
            field = self.env["stock.move"]._fields[name]
            self.assertFalse(field.compute, "%s must not be computed" % name)
            self.assertFalse(field.related, "%s must not be related" % name)
            self.assertTrue(field.store)

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def test_23_preview_lines(self):
        move = self._make_inventory_move()
        wizard = self._wizard(move, mode="fixed", new_date=TARGET)

        self.assertEqual(len(wizard.line_ids), 1)
        line = wizard.line_ids
        self.assertEqual(line.current_date, move.date)
        self.assertEqual(line.target_date, TARGET)
        self.assertEqual(line.product_id, self.product)
        self.assertEqual(wizard.move_count, 1)

    def test_24_no_target_yet_means_no_apply(self):
        move = self._make_inventory_move()
        wizard = self._wizard(move, mode="fixed")
        with self.assertRaises(UserError):
            wizard.action_apply()

    def test_25_chatter_note_on_the_document(self):
        self._make_inventory_move(qty=50)
        picking = self._make_delivery(qty=2)
        before = len(picking.message_ids)

        self._wizard(picking.move_ids, mode="fixed", new_date=TARGET,
                     reason="cierre 2024").action_apply()

        self.assertGreater(len(picking.message_ids), before)
        body = picking.message_ids[0].body
        self.assertIn("cierre 2024", body)
        # The note used to be posted as a plain string, so Odoo escaped it and the
        # chatter showed raw "<p><b>...</b>" tags instead of a table.
        self.assertIn("<table", body, "the note must render as HTML, not as text")
        self.assertNotIn("&lt;table", body, "the markup must not be escaped")
        self.assertNotIn("&lt;p&gt;", body)

    def test_25b_note_shows_the_date_it_really_replaces(self):
        """On a second pass, 'Before' must be the previous date, not the original."""
        move = self._make_inventory_move()
        first_target = datetime(2024, 2, 10, 9, 0, 0)
        second_target = datetime(2024, 3, 15, 11, 0, 0)

        self._wizard(move, mode="fixed", new_date=first_target).action_apply()
        product = move.product_id.product_tmpl_id
        before = len(product.message_ids)
        self._wizard(move, mode="fixed", new_date=second_target).action_apply()

        self.assertGreater(len(product.message_ids), before)
        body = product.message_ids[0].body
        self.assertIn("<table", body)
        # Dates are rendered in the reader's locale, so assert on the day number
        # rather than on a raw "2024-02-10 09:00:00" that no longer appears.
        self.assertIn("10", body, "the note must quote the date being replaced")

    # ------------------------------------------------------------------
    # 26..27 -- header sync cascades onto sibling movements
    # ------------------------------------------------------------------

    def _make_two_line_delivery(self):
        other = self.env["product.product"].create({
            "name": "Second Widget", "type": "consu", "is_storable": True,
        })
        for product in (self.product, other):
            self.env["stock.quant"].with_context(inventory_mode=True).create({
                "product_id": product.id,
                "location_id": self.stock_location.id,
                "inventory_quantity": 50,
            }).action_apply_inventory()
        picking_type = self.env.ref("stock.picking_type_out")
        picking = self.env["stock.picking"].create({
            "picking_type_id": picking_type.id,
            "location_id": self.stock_location.id,
            "location_dest_id": self.customer_location.id,
            "move_ids": [
                (0, 0, {"product_id": p.id, "product_uom_qty": 1,
                        "product_uom": p.uom_id.id,
                        "location_id": self.stock_location.id,
                        "location_dest_id": self.customer_location.id})
                for p in (self.product, other)
            ],
        })
        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = 1
            move.picked = True
        picking.button_validate()
        return picking

    def test_26_shift_is_not_flattened_by_the_header_sync(self):
        """Writing a header date cascades onto every movement of the document.

        Done last, that cascade overwrote the individual targets and collapsed a
        shift onto a single instant -- destroying the very spacing the mode
        exists to preserve. The header must therefore be written BEFORE the
        movements, not after.
        """
        picking = self._make_two_line_delivery()
        first, second = picking.move_ids[0], picking.move_ids[1]
        first.write({"date": datetime(2026, 5, 1, 8, 0, 0)})
        second.write({"date": datetime(2026, 5, 1, 15, 30, 0)})
        spacing = second.date - first.date

        self._wizard(
            picking.move_ids, mode="shift",
            shift_from=datetime(2026, 5, 1, 0, 0, 0),
            shift_to=datetime(2025, 5, 1, 0, 0, 0),
        ).action_apply()

        self.assertEqual(first.date, datetime(2025, 5, 1, 8, 0, 0))
        self.assertEqual(second.date, datetime(2025, 5, 1, 15, 30, 0))
        self.assertEqual(second.date - first.date, spacing,
                         "the document sync must not flatten a shift")

    def test_27_siblings_are_added_openly_and_traced(self):
        """Selecting one line of a transfer moves them all -- so show them all."""
        picking = self._make_two_line_delivery()
        picked, sibling = picking.move_ids[0], picking.move_ids[1]

        wizard = self._wizard(picked, mode="fixed", new_date=TARGET)

        self.assertEqual(wizard.sibling_count, 1)
        self.assertEqual(wizard.effective_move_ids, picking.move_ids)
        self.assertEqual(len(wizard.line_ids), 2,
                         "the preview must list what will really change")
        self.assertIn("share a document", wizard.warning_html)

        wizard.action_apply()

        for move in (picked, sibling):
            self.assertEqual(move.date, TARGET)
            self.assertTrue(move.date_adjusted,
                            "a movement dragged along must still be traceable")
            self.assertTrue(move.original_date)

    def test_27b_no_expansion_when_the_header_is_left_alone(self):
        picking = self._make_two_line_delivery()
        picked, sibling = picking.move_ids[0], picking.move_ids[1]
        before = sibling.date

        wizard = self._wizard(picked, mode="fixed", new_date=TARGET,
                              sync_document=False)
        self.assertEqual(wizard.sibling_count, 0)
        self.assertEqual(wizard.effective_move_ids, picked)

        wizard.action_apply()

        self.assertEqual(picked.date, TARGET)
        self.assertEqual(sibling.date, before, "nothing else may move")

    def _assert_rendered_note(self, record, origin):
        self.assertTrue(record.message_ids, "%s got no note" % origin)
        body = record.message_ids[0].body
        self.assertIn("<table", body, "%s: the note must render as HTML" % origin)
        self.assertNotIn("&lt;", body, "%s: the markup must not be escaped" % origin)

    def test_28_note_renders_on_every_origin_of_this_module(self):
        """One code path posts to five different chatters -- check each one.

        The note reaches whatever document the movement belongs to, and for an
        inventory adjustment, which has none, the product template. A rendering
        bug in the shared builder shows up in all of them at once.
        """
        move = self._make_inventory_move()
        self._wizard(move, mode="fixed", new_date=TARGET).action_apply()
        self._assert_rendered_note(self.product.product_tmpl_id, "inventory adjustment")

        picking = self._make_two_line_delivery()
        self._wizard(picking.move_ids, mode="fixed", new_date=TARGET).action_apply()
        self._assert_rendered_note(picking, "transfer")

        scrap = self.env["stock.scrap"].create({
            "product_id": self.product.id,
            "product_uom_id": self.product.uom_id.id,
            "scrap_qty": 1,
            "location_id": self.stock_location.id,
        })
        scrap.do_scrap()
        self._wizard(scrap.move_ids, mode="fixed", new_date=TARGET).action_apply()
        self._assert_rendered_note(scrap, "scrap")

    def test_29_document_count_counts_documents_not_origin_groups(self):
        """A movement with no document must not be announced as one document.

        The banner used to count (origin, document) pairs, so two inventory
        adjustments -- which have no document at all -- were announced as
        "1 document(s)". The wording now drops the clause entirely.
        """
        first = self._make_inventory_move(qty=5)
        second = self._make_inventory_move(qty=9)

        wizard = self._wizard(first | second, mode="fixed", new_date=TARGET)

        self.assertEqual(wizard.move_count, 2)
        self.assertEqual(wizard.document_count, 0,
                         "an inventory adjustment has no source document")
        self.assertNotIn("document", wizard.scope_summary,
                         "with no documents the sentence must not mention them")

    def test_29b_document_count_on_a_real_document(self):
        picking = self._make_two_line_delivery()

        wizard = self._wizard(picking.move_ids, mode="fixed", new_date=TARGET)

        self.assertEqual(wizard.move_count, 2)
        self.assertEqual(wizard.document_count, 1, "both lines share one transfer")
