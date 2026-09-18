"""Mutations of this module. See stock_landed_cost_variance/tests/mutations.py for the why."""

MUTATIONS = [
    {
        "name": "kardex_live_rows",
        "why": "the Kardex columns stop adding what no stored value carries",
        "file": "models/stock_move.py",
        "old": '        rows = self.variance_line_ids.filtered(lambda r: r.kind != "legacy")',
        "new": "        rows = self.variance_line_ids.browse()",
        "tags": "/stock_landed_cost_variance_kardex",
        "must_fail": ["test_negative_stock_discard_is_added_on_the_entry"],
    },
]
