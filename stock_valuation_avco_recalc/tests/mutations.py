"""Mutations of this module. See stock_landed_cost_variance/tests/mutations.py for the why."""

MUTATIONS = [
    {
        "name": "rebuild_dated_rows",
        "why": "a rebuild changes the value of periods already reported",
        "file": "models/stock_move_recalc.py",
        "old": '        if vals:\n            self.env["stock.value.variance"].sudo().create(vals)\n',
        "new": "",
        "tags": "/stock_valuation_avco_recalc",
        "must_fail": ["test_periods_before_the_date_keep_their_values"],
    },
]
