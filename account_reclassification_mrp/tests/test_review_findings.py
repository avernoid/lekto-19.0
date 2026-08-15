"""Regression tests for the defects found in the adversarial review.

Each test is named after the finding it pins. They all failed before the fix.
"""
from odoo import fields
from odoo.tests import tagged

from .test_manufacturing_split import TestManufacturingSplit


@tagged("post_install", "-at_install")
class TestReviewFindings(TestManufacturingSplit):

    def test_13_wip_wizard_still_works(self):
        """D1: the native WIP accounting wizard calls _cal_cost(date)."""
        finished, _consumable, bom = self._scenario("N13")
        mo = self.env["mrp.production"].create({
            "product_id": finished.id, "bom_id": bom.id, "product_qty": 1.0})
        mo.action_confirm()
        self._produce(mo)

        wizard = self.env["mrp.account.wip.accounting"].create({
            "reversal_date": fields.Date.context_today(mo),
        })
        self.assertIsNotNone(
            wizard.line_ids,
            "the wizard must build its lines instead of raising a TypeError")

    def test_14_cal_cost_is_multi_record_and_scoped(self):
        """D2: _cal_cost() is called on whole recordsets by native code."""
        finished, _consumable, bom = self._scenario("N14")
        mo = self._run(finished, bom)

        self.assertEqual(mo.workorder_ids._cal_cost(), 29.0)
        self.assertEqual(
            mo.workorder_ids.with_context(reclass_skip_labour_entry=True)._cal_cost(),
            29.0, "an unflagged work centre keeps its cost")

        self.workcenter.reclass_skip_labour_entry = True
        self.assertEqual(
            mo.workorder_ids.with_context(reclass_skip_labour_entry=True)._cal_cost(),
            0.0, "a flagged one drops out only inside the labour entry")
        self.assertEqual(mo.workorder_ids._cal_cost(), 29.0,
                         "and never outside it, so valuation is untouched")

    def test_15_single_origin_still_reaches_its_account(self):
        """D3: one origin on a different account is a split, not a no-op."""
        consumable = self.env["product.product"].create({
            "name": "N15 Consumable", "is_storable": False,
            "standard_price": 5.0, "categ_id": self.category_avco_auto.id,
        })
        consumable.reclass_recognition_account_id = self.account_consumable
        finished = self._create_product("N15 Finished", 0.0, quantity=0,
                                        category=self.category_avco_auto)
        finished.reclass_production_account_id = self.account_materials
        bom = self.env["mrp.bom"].create({
            "product_tmpl_id": finished.product_tmpl_id.id,
            "product_id": finished.id, "product_qty": 1.0, "type": "normal",
            "bom_line_ids": [(0, 0, {"product_id": consumable.id, "product_qty": 1.0})],
        })

        mo = self._run(finished, bom)
        entry, move = self._finished_entry(mo)

        self.assertEqual(move.value, 5.0)
        self.assertEqual(
            self._credits(entry), {self.account_consumable: 5.0},
            "the whole cost comes from the consumable: its account must be used")

    def test_16_two_consumables_two_accounts(self):
        """D6: each consumable lands on the account it resolves."""
        other_account = self._make_account("RECCONS2", "Production - Consumable 2")
        cons_a = self.env["product.product"].create({
            "name": "N16 Cons A", "is_storable": False, "standard_price": 100.0,
            "categ_id": self.category_avco_auto.id,
        })
        cons_b = self.env["product.product"].create({
            "name": "N16 Cons B", "is_storable": False, "standard_price": 900.0,
            "categ_id": self.category_avco_auto.id,
        })
        cons_a.reclass_recognition_account_id = self.account_consumable
        cons_b.reclass_recognition_account_id = other_account
        finished = self._create_product("N16 Finished", 0.0, quantity=0,
                                        category=self.category_avco_auto)
        finished.reclass_production_account_id = self.account_materials
        bom = self.env["mrp.bom"].create({
            "product_tmpl_id": finished.product_tmpl_id.id,
            "product_id": finished.id, "product_qty": 1.0, "type": "normal",
            "bom_line_ids": [
                (0, 0, {"product_id": cons_a.id, "product_qty": 1.0}),
                (0, 0, {"product_id": cons_b.id, "product_qty": 1.0}),
            ],
        })

        mo = self._run(finished, bom)
        entry, _move = self._finished_entry(mo)

        self.assertEqual(
            self._credits(entry),
            {self.account_consumable: 100.0, other_account: 900.0},
            "each consumable on its own account, not all on the first one")

    def test_17_operations_always_use_the_configured_account(self):
        """The configured account is never ignored, not even for mixed centres.

        D5 pinned the opposite rule -- work orders that ended up in the labour
        entry were credited on the location account instead of the configured
        one -- and it was reverted by decision of the user: the configuration is
        obeyed, and configuring it coherently is the user's job.

        With one flagged work centre and one booked, ALL the operations (20 + 29)
        are credited on the operations account, and the debit of the labour entry
        stays on the location account. That leftover is the visible price of an
        incoherent configuration, not a defect: either suppress the labour entry
        for every centre, or leave the operations account empty.
        """
        other_workcenter = self.env["mrp.workcenter"].create({
            "name": "N17 Workcenter B", "costs_hour": 60.0,
            "company_id": self.company.id, "reclass_skip_labour_entry": True,
        })
        finished, consumable, bom = self._scenario("N17")
        self.env["mrp.routing.workcenter"].create({
            "bom_id": bom.id, "name": "N17 Op B",
            "workcenter_id": other_workcenter.id, "time_cycle_manual": 20.0,
        })
        finished.reclass_production_account_id = self.account_materials
        consumable.reclass_recognition_account_id = self.account_consumable
        finished.reclass_operations_account_id = self.account_operations

        mo = self._run(finished, bom)
        entry, move = self._finished_entry(mo)

        self.assertEqual(move.value, 109.10, "the value of the product is untouched")
        self.assertEqual(
            self._credits(entry),
            {self.account_materials: 60.00, self.account_consumable: 0.10,
             self.account_operations: 49.00},
            "both work centres are recognised on the configured account")
        self._assert_balanced(entry)

        # Scope: the labour entry and the recognition entry. The consumption of
        # the storable components also touches the location account, but that is
        # native behaviour driven by their own (here unconfigured) category, and
        # not what this test is about.
        labour = self._labour_entry(mo)
        self.assertTrue(labour, "the booked work centre must still post its entry")
        location_balance = sum((labour | entry).line_ids.filtered(
            lambda line: line.account_id == self.account_location).mapped("balance"))
        self.assertEqual(
            location_balance, 29.0,
            "the labour debit stays there: the user configured it that way")

    def test_18_operations_round_per_work_order_like_native(self):
        """D4: the operations credit must equal what the labour entry debits."""
        finished, _consumable, bom = self._scenario("N18")
        bom.operation_ids.unlink()
        for index in range(3):
            self.env["mrp.routing.workcenter"].create({
                "bom_id": bom.id, "name": "N18 Op %s" % index,
                "workcenter_id": self.workcenter.id, "time_cycle_manual": 10.005,
            })
        finished.reclass_production_account_id = self.account_materials

        mo = self._run(finished, bom)
        entry, _move = self._finished_entry(mo)

        labour_debit = sum(self._labour_entry(mo).line_ids.filtered(
            lambda line: line.account_id == self.account_location).mapped("debit"))
        operations_credit = self._credits(entry).get(self.account_location, 0.0)
        self.assertTrue(labour_debit, "the labour entry must exist for this test")
        self.assertEqual(
            operations_credit, labour_debit,
            "credit and debit on the location account must match to the cent")
