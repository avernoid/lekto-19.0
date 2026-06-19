# Copyright 2026 Ganemo
# License OPL-1 (Odoo Proprietary License v1.0) - See LICENSE file.
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import AnalyticStockCommon


@tagged("post_install", "-at_install")
class TestStockScrap(AnalyticStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Scrap moves are valued against the scrap location, so it needs a
        # counterpart valuation account too.
        scrap = cls.env["stock.scrap"].new({"company_id": cls.company.id})
        cls.scrap_location = scrap.scrap_location_id
        cls.scrap_location.valuation_account_id = cls.counterpart_account

    def _create_scrap(self, distribution=False):
        return self.env["stock.scrap"].create(
            {
                "product_id": self.product.id,
                "scrap_qty": 1.0,
                "product_uom_id": self.product.uom_id.id,
                "location_id": self.stock_location.id,
                "analytic_distribution": distribution or False,
            }
        )

    def test_scrap_with_analytic_stamps_entry(self):
        self._set_on_hand(self.product, 1)
        scrap = self._create_scrap(self.distribution)
        scrap.action_validate()
        self.assertEqual(scrap.state, "done")
        move = scrap.move_ids
        counterpart = move.account_move_id.line_ids.filtered(
            lambda line: line.account_id != self.valuation_account
        )
        self.assertTrue(counterpart)
        for line in counterpart:
            self.assertEqual(line.analytic_distribution, self.distribution)

    def test_scrap_optional(self):
        self._create_applicability(applicability="optional")
        self._set_on_hand(self.product, 1)
        scrap = self._create_scrap()
        scrap.action_validate()
        self.assertEqual(scrap.state, "done")

    def test_scrap_mandatory_blocks(self):
        self._create_applicability(applicability="mandatory")
        self._set_on_hand(self.product, 1)
        scrap = self._create_scrap()
        with self.assertRaises(ValidationError):
            scrap.action_validate()
