"""Mutations of this module. See stock_landed_cost_variance/tests/mutations.py for the why."""

MUTATIONS = [
    {
        "name": "ple_131_date_rule",
        "why": "a period already filed no longer regenerates identically",
        "file": "wizard/stock_move_ple_report.py",
        "old": "                total_cost -= self._l10n_pe_folded_later(move)\n",
        "new": "",
        "tags": "/l10n_pe_reports_stock_transfer_document",
        "must_fail": ["test_landed_cost_in_the_next_period_then_more"],
    },
]
