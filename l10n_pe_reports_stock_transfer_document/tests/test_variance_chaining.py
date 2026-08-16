import base64

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "post_install_l10n", "-at_install")
class TestPleVarianceChaining(AccountTestInvoicingCommon):
    """The property the whole change is validated against.

    A landed cost applied after part of the goods left leaves the ledger
    overstated: the receipt carries the whole amount while only the part still
    in stock belongs there.  Correcting one period without correcting the
    opening of the next would swap a ledger that is wrong but *continuous* for
    one that is discontinuous, which is worse -- the difference would come back
    every period, with no line to point at.

    So the assertion is not "January is right": it is "January closes exactly
    where February opens", and both on the corrected figure.
    """

    @classmethod
    @AccountTestInvoicingCommon.setup_country("pe")
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.company.country_id = cls.env.ref("base.pe")
        cls.company.vat = "20512528458"
        cls.categ = cls.env["product.category"].create({"name": "PLE variance"})
        cls.categ.with_company(cls.company).write({
            "property_cost_method": "average",
            "property_valuation": "real_time",
        })
        cls.product = cls.env["product.product"].create({
            "name": "PLE-VAR",
            "is_storable": True,
            "categ_id": cls.categ.id,
            "standard_price": 500.0,
        })
        cls.freight = cls.env["product.product"].create({
            "name": "PLE-FREIGHT", "type": "service", "landed_cost_ok": True,
        })
        cls.wh = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1)
        cls.stock_loc = cls.wh.lot_stock_id
        cls.supplier_loc = cls.env.ref("stock.stock_location_suppliers")
        cls.customer_loc = cls.env.ref("stock.stock_location_customers")

    def setUp(self):
        super().setUp()
        if "stock.value.variance" not in self.env:
            self.skipTest("stock_landed_cost_variance is not installed")

    # ------------------------------------------------------------------
    def _move(self, code, src, dest, qty, date):
        ptype = self.env["stock.picking.type"].search(
            [("code", "=", code), ("warehouse_id", "=", self.wh.id)], limit=1)
        picking = self.env["stock.picking"].create({
            "picking_type_id": ptype.id,
            "location_id": src.id,
            "location_dest_id": dest.id,
            "move_ids": [Command.create({
                "product_id": self.product.id,
                "product_uom_qty": qty,
                "product_uom": self.product.uom_id.id,
                "location_id": src.id,
                "location_dest_id": dest.id,
            })],
        })
        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            if move.move_line_ids:
                move.move_line_ids[0].quantity = qty
            else:
                move.quantity = qty
            move.picked = True
        picking.button_validate()
        picking.move_ids.write({"date": date})
        return picking

    def _report(self, date_from, date_to):
        """Lines of the 13.1 that belong to OUR product.

        The report covers every product of the company, so indexing the raw
        output positionally only holds on a database where nothing else moved
        in the window.  That stops being true the moment demo data or another
        module's fixture puts a movement in the same month: the assertion then
        reads a stranger's line and fails for a reason unrelated to what is
        being tested.
        """
        wizard = self.env["l10n_pe.stock.ple.wizard"].create({
            "date_from": date_from, "date_to": date_to,
        })
        wizard.get_ple_report_13_1()
        raw = base64.b64decode(wizard.report_data).decode()
        lines = [line.split("|") for line in raw.split("\n") if line.strip()]
        ours = [line for line in lines
                if any(self.product.name in field for field in line)]
        self.assertTrue(ours, "the product under test produced no 13.1 line")
        return ours

    # ------------------------------------------------------------------
    def test_january_closes_where_february_opens(self):
        receipt = self._move("incoming", self.supplier_loc, self.stock_loc,
                             5.0, "2026-01-10 10:00:00")
        self._move("outgoing", self.stock_loc, self.customer_loc,
                   3.0, "2026-01-20 10:00:00")

        cost = self.env["stock.landed.cost"].create({
            "picking_ids": [Command.set(receipt.ids)],
            "account_journal_id": self.company_data["default_journal_misc"].id,
            "cost_lines": [Command.create({
                "product_id": self.freight.id,
                "name": "freight",
                "price_unit": 250.0,
                "split_method": "equal",
            })],
        })
        cost.compute_landed_cost()
        cost.button_validate()

        variance = self.env["stock.value.variance"].search(
            [("move_id", "in", receipt.move_ids.ids)])
        self.assertAlmostEqual(variance.expensed_amount, 150.0, 2,
                               "3 of the 5 units had already gone")

        january = self._report("2026-01-01", "2026-01-31")
        february = self._report("2026-02-01", "2026-02-28")

        # Counting from the end of a 13.1 line: '' | state | running value |
        # unit cost | running qty.
        january_close = float(january[-1][-3])
        february_open = float(february[0][-3])
        self.assertAlmostEqual(float(january[-1][-4]), 550.0, 2,
                               "closing unit cost is the landed one, not 625")

        self.assertAlmostEqual(january_close, 1100.0, 2,
                               "2 units at the landed cost of 550")
        self.assertAlmostEqual(
            february_open, january_close, 2,
            "the ledger must be continuous across the period boundary")

        # And it agrees with what the valuation engine says the stock is worth.
        self.assertAlmostEqual(
            january_close,
            self.product.with_company(self.company).total_value, 2)

    def test_the_decrease_gets_its_own_line(self):
        receipt = self._move("incoming", self.supplier_loc, self.stock_loc,
                             5.0, "2026-01-10 10:00:00")
        self._move("outgoing", self.stock_loc, self.customer_loc,
                   3.0, "2026-01-20 10:00:00")
        cost = self.env["stock.landed.cost"].create({
            "picking_ids": [Command.set(receipt.ids)],
            "account_journal_id": self.company_data["default_journal_misc"].id,
            "cost_lines": [Command.create({
                "product_id": self.freight.id, "name": "freight",
                "price_unit": 250.0, "split_method": "equal",
            })],
        })
        cost.compute_landed_cost()
        cost.button_validate()

        january = self._report("2026-01-01", "2026-01-31")
        # Operation type sits at column 13; the decrease carries 99 ("Otros"),
        # the native increase keeps the 26 the standard already emits.
        op_types = [line[13] for line in january]
        self.assertIn("26", op_types, "the native landed cost line survives")
        self.assertIn("99", op_types, "the decrease is emitted as its own line")

        cuos = [line[1] for line in january]
        self.assertEqual(len(cuos), len(set(cuos)),
                         "every line needs its own CUO namespace")

    def test_absorbed_variance_emits_nothing(self):
        """Once a recalculation owns the correction, the report must not apply
        it a second time."""
        receipt = self._move("incoming", self.supplier_loc, self.stock_loc,
                             5.0, "2026-01-10 10:00:00")
        self._move("outgoing", self.stock_loc, self.customer_loc,
                   3.0, "2026-01-20 10:00:00")
        cost = self.env["stock.landed.cost"].create({
            "picking_ids": [Command.set(receipt.ids)],
            "account_journal_id": self.company_data["default_journal_misc"].id,
            "cost_lines": [Command.create({
                "product_id": self.freight.id, "name": "freight",
                "price_unit": 250.0, "split_method": "equal",
            })],
        })
        cost.compute_landed_cost()
        cost.button_validate()
        self.env["stock.value.variance"].search(
            [("move_id", "in", receipt.move_ids.ids)]).absorbed = True

        january = self._report("2026-01-01", "2026-01-31")
        self.assertNotIn("99", [line[13] for line in january],
                         "an absorbed variance contributes no line")
        self.assertAlmostEqual(float(january[-1][-3]), 1250.0, 2,
                               "back to the uncorrected ledger, as intended")
