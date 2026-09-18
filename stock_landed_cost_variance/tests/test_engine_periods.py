from datetime import timedelta

from odoo.tests import tagged

from .common import RevaluationCommon


@tagged("post_install", "-at_install")
class TestEnginePeriods(RevaluationCommon):
    """Time attribution (design v4, D7): value known at a date == stock valuation account at that date,
    a closed period keeps its figure after later events, and every period opens where the previous closed.
    """

    def _check_periods(self, filed=None):
        figures = {}
        previous = None
        for name, (p_from, p_to) in (("P1", self.p1), ("P2", self.p2), ("P3", self.p3)):
            known = self.known_at(p_to)
            self.assertAlmostEqual(known, self.balance(self.acc_valuation, day=p_to), 2,
                                   f"{name}: value known at the period end differs from the accounting")
            if previous is not None:
                self.assertAlmostEqual(self.known_at(p_from - timedelta(days=1)), previous, 2)
            if filed and name in filed:
                self.assertAlmostEqual(known, filed[name], 2, f"{name} changed after a later event")
            figures[name] = known
            previous = known
        return figures

    def test_landed_cost_in_the_next_period_then_more(self):
        self.set_periods()
        po = self.purchase(5, 500, day=self.day(self.p1, 3))
        self.bill(po, day=self.day(self.p1, 3))
        self.invoice(self.sale(3, day=self.day(self.p1, 10)), day=self.day(self.p1, 10))
        filed = self._check_periods()
        self.assertAlmostEqual(filed["P1"], 1000.0, 2)
        self.landed_cost(po, 250, day=self.day(self.p2, 5))
        filed.update({"P2": self._check_periods(filed={"P1": filed["P1"]})["P2"]})
        self.assertAlmostEqual(filed["P2"], 1100.0, 2)
        self.invoice(self.sale(1, day=self.day(self.p3, 1)), day=self.day(self.p3, 1))
        self.landed_cost(po, 100, day=self.day(self.p3, 1))
        final = self._check_periods(filed={"P1": filed["P1"], "P2": filed["P2"]})
        self.assertAlmostEqual(final["P3"], 570.0, 2)

    def test_return_of_an_earlier_sale_after_a_landed_cost(self):
        self.set_periods()
        po = self.purchase(5, 500, day=self.day(self.p1, 3))
        self.bill(po, day=self.day(self.p1, 3))
        so = self.sale(3, day=self.day(self.p1, 10))
        inv = self.invoice(so, day=self.day(self.p1, 10))
        self.landed_cost(po, 250, day=self.day(self.p2, 5))
        filed = self._check_periods()
        self.return_goods(so, 1, day=self.day(self.p3, 1))
        self.refund(inv, 1, day=self.day(self.p3, 1))
        final = self._check_periods(filed={"P1": filed["P1"], "P2": filed["P2"]})
        self.assertAlmostEqual(final["P3"], 1650.0, 2)

    def test_events_are_listed_in_their_own_period(self):
        self.set_periods()
        po = self.purchase(5, 500, day=self.day(self.p1, 3))
        self.bill(po, day=self.day(self.p1, 3))
        self.invoice(self.sale(3, day=self.day(self.p1, 10)), day=self.day(self.p1, 10))
        self.landed_cost(po, 250, day=self.day(self.p2, 5))
        product = self.product.with_company(self.company)
        self.assertFalse(product._variance_events_in_period(*self.p1), "nothing happened in P1 after the fact")
        events = product._variance_events_in_period(*self.p2)
        self.assertEqual({e["kind"] for _m, e in events}, {"landed_cost", "exit"})
        self.assertAlmostEqual(sum(e["value"] for _m, e in events), 100.0, 2, "+250 freight, -150 sold units")
        self.assertTrue(all(e["date"] == self.day(self.p2, 5) for _m, e in events))


@tagged("post_install", "-at_install")
class TestEnginePeriodsFifo(TestEnginePeriods):
    """The same period invariants with a FIFO product: the measurements were taken with both methods,
    and FIFO takes a different path (stack replay instead of the average report)."""

    allow_inherited_tests_method = True
    COST_METHOD = "fifo"
