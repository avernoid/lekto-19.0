from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.mrp_account.tests.common import TestBomPriceCommon


@tagged("post_install", "-at_install")
class TestManufacturingSplit(TestBomPriceCommon):
    """The counterpart of the manufacturing entry, broken down by cost origin.

    Reference scenario, mirroring the real case this module was built for:
    two storable components (40 + 20), one non-storable consumable (0.10) and one
    work centre operation (29.00) => a finished product worth 89.10.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_location = cls._make_account("RECLOC", "Production Location")
        cls.account_materials = cls._make_account("RECMAT", "Production - Materials")
        cls.account_consumable = cls._make_account("RECCONS", "Production - Consumable")
        cls.account_operations = cls._make_account("RECOPS", "Production - Operations")
        cls.production_location = cls.env["stock.location"].search([
            ("usage", "=", "production"),
            ("company_id", "=", cls.company.id),
        ], limit=1)
        cls.production_location.valuation_account_id = cls.account_location
        cls.workcenter = cls.env["mrp.workcenter"].create({
            "name": "REC Workcenter", "costs_hour": 60.0, "company_id": cls.company.id,
        })

    @classmethod
    def _make_account(cls, code, name):
        return cls.env["account.account"].create({
            "name": name, "code": code, "account_type": "asset_current",
        })

    def _scenario(self, name="REC"):
        comp_a = self._create_product("%s Comp A" % name, 40.0, quantity=100,
                                      category=self.category_avco_auto)
        comp_b = self._create_product("%s Comp B" % name, 20.0, quantity=100,
                                      category=self.category_avco_auto)
        consumable = self.env["product.product"].create({
            "name": "%s Consumable" % name, "is_storable": False,
            "standard_price": 0.10, "categ_id": self.category_avco_auto.id,
        })
        finished = self._create_product("%s Finished" % name, 0.0, quantity=0,
                                        category=self.category_avco_auto)
        bom = self.env["mrp.bom"].create({
            "product_tmpl_id": finished.product_tmpl_id.id,
            "product_id": finished.id,
            "product_qty": 1.0,
            "type": "normal",
            "bom_line_ids": [
                (0, 0, {"product_id": comp_a.id, "product_qty": 1.0}),
                (0, 0, {"product_id": comp_b.id, "product_qty": 1.0}),
                (0, 0, {"product_id": consumable.id, "product_qty": 1.0}),
            ],
            "operation_ids": [
                (0, 0, {"name": "%s Op" % name, "workcenter_id": self.workcenter.id,
                        "time_cycle_manual": 29.0}),
            ],
        })
        return finished, consumable, bom

    def _run(self, finished, bom, quantity=1.0):
        mo = self.env["mrp.production"].create({
            "product_id": finished.id, "bom_id": bom.id, "product_qty": quantity})
        mo.action_confirm()
        mo = self._produce(mo)
        mo.button_mark_done()
        return mo

    def _finished_entry(self, mo):
        move = mo.move_finished_ids.filtered(
            lambda m: m.product_id == mo.product_id and m.state == "done")
        return move.account_move_id, move

    def _credits(self, entry):
        """Credits of the entry grouped by account.

        One entry can carry several output moves (finished goods + byproducts),
        so the amounts must be added up, never overwritten.
        """
        credits = {}
        for line in entry.line_ids:
            if line.credit:
                credits[line.account_id] = round(
                    credits.get(line.account_id, 0.0) + line.credit, 2)
        return credits

    def _credits_by_product(self, entry):
        """Credits grouped by (product, account); the split copies the product."""
        credits = {}
        for line in entry.line_ids:
            if line.credit:
                key = (line.product_id, line.account_id)
                credits[key] = round(credits.get(key, 0.0) + line.credit, 2)
        return credits

    def _assert_balanced(self, entry):
        self.assertAlmostEqual(
            sum(entry.line_ids.mapped("balance")), 0.0, places=6,
            msg="the entry must balance")

    # -------------------------------------------------------------------------
    # SIN CONFIGURAR: NATIVO
    # -------------------------------------------------------------------------

    def test_01_unconfigured_keeps_the_native_single_line(self):
        """No account configured anywhere: one counterpart line, as native."""
        finished, _consumable, bom = self._scenario("N1")
        mo = self._run(finished, bom)

        entry, move = self._finished_entry(mo)
        self.assertEqual(move.value, 89.10)
        self.assertEqual(len(entry.line_ids), 2)
        self.assertEqual(self._credits(entry), {self.account_location: 89.10})

    # -------------------------------------------------------------------------
    # DESGLOSE COMPLETO
    # -------------------------------------------------------------------------

    def test_02_full_breakdown(self):
        """Materials, consumable and operations, each on its own account."""
        finished, consumable, bom = self._scenario("N2")
        finished.categ_id = self.category_avco_auto
        finished.reclass_production_account_id = self.account_materials
        consumable.reclass_recognition_account_id = self.account_consumable
        finished.reclass_operations_account_id = self.account_operations

        mo = self._run(finished, bom)
        entry, move = self._finished_entry(mo)

        self.assertEqual(move.value, 89.10)
        self.assertEqual(
            self._credits(entry),
            {
                self.account_materials: 60.00,
                self.account_consumable: 0.10,
                # The configured account is always used, labour entry or not.
                self.account_operations: 29.00,
            },
        )
        self._assert_balanced(entry)
        self.assertEqual(sum(entry.line_ids.mapped("debit")), 89.10,
                         "the debit to stock must not change")

    def test_03_only_the_consumable_configured(self):
        """No operations account: the fallback is the production location.

        Last step of the resolution chain, and the account the labour entry
        debits, so an order with nothing configured for its operations keeps
        clearing that location exactly as it did before.
        """
        finished, consumable, bom = self._scenario("N3")
        finished.reclass_production_account_id = self.account_materials
        consumable.reclass_recognition_account_id = self.account_consumable

        mo = self._run(finished, bom)
        entry, _move = self._finished_entry(mo)

        self.assertEqual(
            self._credits(entry),
            {self.account_materials: 60.00, self.account_consumable: 0.10,
             self.account_location: 29.00},
            "with no operations account configured the location one applies")

    def test_04_consumable_without_account_falls_in_the_remainder(self):
        """A consumable with no account of its own is never lost."""
        finished, _consumable, bom = self._scenario("N4")
        finished.reclass_production_account_id = self.account_materials
        finished.reclass_operations_account_id = self.account_operations

        mo = self._run(finished, bom)
        entry, _move = self._finished_entry(mo)

        self.assertEqual(
            self._credits(entry),
            {self.account_materials: 60.10, self.account_operations: 29.00})

    # -------------------------------------------------------------------------
    # CASOS LIMITE
    # -------------------------------------------------------------------------

    def test_05_standard_cost_falls_back_to_native(self):
        """The cost does not decompose: the module must not split."""
        finished, consumable, bom = self._scenario("N5")
        finished.categ_id = self.category_standard_auto
        finished.standard_price = 500.0
        finished.reclass_production_account_id = self.account_materials
        consumable.reclass_recognition_account_id = self.account_consumable
        finished.reclass_operations_account_id = self.account_operations

        mo = self._run(finished, bom)
        entry, move = self._finished_entry(mo)

        self.assertEqual(move.value, 500.0)
        self.assertEqual(
            self._credits(entry), {self.account_materials: 500.0},
            "a standard-cost product keeps a single counterpart line")

    def test_06_byproduct_is_prorated(self):
        """Byproduct with a cost share: each output splits by the same ratio."""
        byproduct = self._create_product("N6 Sub", 0.0, quantity=0,
                                         category=self.category_avco_auto)
        finished, consumable, bom = self._scenario("N6")
        bom.write({"byproduct_ids": [
            (0, 0, {"product_id": byproduct.id, "product_qty": 1.0, "cost_share": 30.0})]})
        finished.reclass_production_account_id = self.account_materials
        consumable.reclass_recognition_account_id = self.account_consumable
        finished.reclass_operations_account_id = self.account_operations
        byproduct.reclass_production_account_id = self.account_materials
        byproduct.reclass_operations_account_id = self.account_operations

        mo = self._run(finished, bom)
        entry, move = self._finished_entry(mo)

        self.assertAlmostEqual(move.value, 89.10 * 0.70, places=2)
        # The entry carries BOTH outputs, so its totals are the whole batch.
        self.assertEqual(
            self._credits(entry),
            {self.account_materials: 60.00, self.account_consumable: 0.10,
             self.account_operations: 29.00},
            "summed over both outputs, the breakdown is the full cost")
        self._assert_balanced(entry)
        # And each output carries its own prorated share.
        by_product = self._credits_by_product(entry)
        self.assertAlmostEqual(
            by_product[(mo.product_id, self.account_operations)], 29.00 * 0.70, places=2)
        self.assertAlmostEqual(
            by_product[(byproduct, self.account_operations)], 29.00 * 0.30, places=2)

    def test_07_backorder_each_batch_splits_on_its_own(self):
        """Two partial postings: each entry balances and splits independently."""
        finished, consumable, bom = self._scenario("N7")
        finished.reclass_production_account_id = self.account_materials
        consumable.reclass_recognition_account_id = self.account_consumable
        finished.reclass_operations_account_id = self.account_operations

        mo = self.env["mrp.production"].create({
            "product_id": finished.id, "bom_id": bom.id, "product_qty": 2.0})
        mo.action_confirm()
        mo = self._produce(mo, 1.0)
        action = mo.button_mark_done()
        wizard = self.env[action["res_model"]].with_context(
            **action.get("context", {})).create({})
        wizard.action_backorder()

        entry, _move = self._finished_entry(mo)
        self.assertEqual(
            self._credits(entry),
            {self.account_materials: 60.00, self.account_consumable: 0.10,
             self.account_operations: 29.00})

        backorder = mo.production_group_id.production_ids - mo
        backorder = self._produce(backorder)
        backorder.button_mark_done()
        entry2, _move2 = self._finished_entry(backorder)
        self.assertEqual(
            self._credits(entry2),
            {self.account_materials: 60.00, self.account_consumable: 0.10,
             self.account_operations: 29.00})

    # -------------------------------------------------------------------------
    # FLAG POR CENTRO DE TRABAJO
    # -------------------------------------------------------------------------

    def test_08_workcenter_flag_suppresses_the_labour_entry(self):
        """No labour entry, and the product keeps exactly the same value."""
        finished, _consumable, bom = self._scenario("N8")
        self.workcenter.reclass_skip_labour_entry = True

        mo = self._run(finished, bom)
        entry, move = self._finished_entry(mo)

        self.assertEqual(move.value, 89.10,
                         "the value of the product must not change")
        labour = self.env["account.move"].search(
            [("ref", "=", "%s - Labour" % mo.name)])
        self.assertFalse(labour, "the labour entry must not be created")
        # With nothing configured the recognition entry keeps the single native
        # counterpart line, so the location account carries the value of the
        # product and the flag leaves nothing extra behind.
        self.assertEqual(self._credits(entry), {self.account_location: 89.10})

    def test_09_flag_does_not_touch_analytics(self):
        """Analytic entries of the work order keep working natively."""
        analytic_plan = self.env["account.analytic.plan"].create({"name": "REC Plan"})
        analytic_account = self.env["account.analytic.account"].create({
            "name": "REC Cost Centre", "plan_id": analytic_plan.id})
        self.workcenter.write({
            "reclass_skip_labour_entry": True,
            "analytic_distribution": {str(analytic_account.id): 100.0},
        })
        finished, _consumable, bom = self._scenario("N9")

        mo = self._run(finished, bom)

        self.assertTrue(
            mo.workorder_ids.wc_analytic_account_line_ids,
            "the analytic lines of the work centre must still be created")

    def test_10_flag_and_split_together(self):
        """Flag + operations account on a recognition account: no residue."""
        finished, consumable, bom = self._scenario("N10")
        self.workcenter.reclass_skip_labour_entry = True
        finished.reclass_production_account_id = self.account_materials
        consumable.reclass_recognition_account_id = self.account_consumable
        finished.reclass_operations_account_id = self.account_operations

        mo = self._run(finished, bom)
        entry, move = self._finished_entry(mo)

        self.assertEqual(move.value, 89.10)
        self.assertEqual(
            self._credits(entry),
            {self.account_materials: 60.00, self.account_consumable: 0.10,
             self.account_operations: 29.00},
            "the operations are recognised even though no labour entry exists")
        # Scope: the recognition entry and the labour entry, which is the pair
        # this module writes. The consumption of the storable components also
        # touches the location account, but that is native behaviour driven by
        # their own (here unconfigured) category.
        labour = self.env["account.move"].search(
            [("ref", "=", "%s - Labour" % mo.name)])
        self.assertFalse(labour, "the labour entry must not be created")
        location_balance = sum(entry.line_ids.filtered(
            lambda line: line.account_id == self.account_location).mapped("balance"))
        self.assertEqual(
            location_balance, 0.0,
            "the recognition entry must not touch the production location account")

    # -------------------------------------------------------------------------
    # RESILIENCIA
    # -------------------------------------------------------------------------

    @mute_logger("odoo.addons.account_reclassification_mrp.models.stock_move")
    def test_11_any_failure_falls_back_to_the_single_line(self):
        """Whatever blows up in the breakdown, the native entry stands."""
        finished, consumable, bom = self._scenario("N11")
        finished.reclass_production_account_id = self.account_materials
        consumable.reclass_recognition_account_id = self.account_consumable

        def _boom(move_self):
            raise ValueError("simulated future incompatibility")

        self.patch(type(self.env["stock.move"]), "_reclass_mrp_breakdown", _boom)
        mo = self._run(finished, bom)
        entry, move = self._finished_entry(mo)

        self.assertEqual(self._credits(entry), {self.account_materials: 89.10})
        self._assert_balanced(entry)
        self.assertEqual(move.value, 89.10)

    def test_12_non_manufacturing_moves_are_untouched(self):
        """A plain receipt keeps behaving exactly as the base module does."""
        product = self._create_product("N12 Plain", 10.0, quantity=0,
                                       category=self.category_avco_auto)
        move = self._make_in_move(product, 5.0, unit_cost=10.0)
        self.assertFalse(move.production_id)
        self.assertFalse(move.account_move_id,
                         "no account on the supplier location: still no entry")
