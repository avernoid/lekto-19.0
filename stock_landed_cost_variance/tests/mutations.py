"""Mutations of this module: break one correction and the tests that must notice.

They live here, next to the code they protect, so a refactor that moves a line updates its mutation in the
same commit. The runner is ``test_matrix_stock_valuation/tools/check_mutations.py``; it reports STALE
instead of passing quietly when the text to break is no longer there.

Add one whenever a correction is added: a test that cannot fail protects nothing.
"""

MUTATIONS = [
    {
        "name": "fold_exits",
        "why": "the exits are not rewritten to the engine's cost",
        "file": "models/stock_move.py",
        "old": "                move.value = currency.round(target)\n",
        "new": "",
        "tags": "/stock_landed_cost_variance",
        "must_fail": ["test_a_landed_cost_after_the_sale_was_invoiced"],
    },
    {
        "name": "cogs_already_posted",
        "why": "the next invoice of the same line recovers the adjustment again",
        "file": "models/account_move_line.py",
        "old": "        value = super()._get_posted_cogs_value()",
        "new": "        return super()._get_posted_cogs_value()\n        value = super()._get_posted_cogs_value()",
        "tags": "/stock_landed_cost_variance",
        "must_fail": ["test_f_partial_invoice_next_invoice_does_not_recover_twice"],
    },
    {
        "name": "credit_note_reversal",
        "why": "a credit note does not give back the share of our adjustment",
        "file": "models/stock_value_revaluation.py",
        "old": "    def _variance_reverse_for_refund(self, refund):",
        "new": "    def _variance_reverse_for_refund(self, refund):\n        return self.browse()",
        "tags": "/stock_landed_cost_variance",
        "must_fail": ["test_e3_credit_note_after_landed_cost_reverses_our_share"],
    },
    {
        "name": "lot_gap",
        "why": "the value Odoo drops on a FIFO lot is not recorded",
        "file": "models/stock_move.py",
        "old": 'if product.lot_valuated and product.cost_method == "fifo" \\',
        "new": "if False \\",
        "tags": "/stock_landed_cost_variance",
        "must_fail": ["test_fifo_lot_with_two_entries_books_the_native_gap"],
    },
    {
        "name": "production_cascade",
        "why": "manufactured goods keep the old cost for ever",
        "file": "models/stock_value_revaluation.py",
        "old": "    def _variance_cascade_production(self, production, amount, account, date, parent):",
        "new": ("    def _variance_cascade_production(self, production, amount, account, date, parent):\n"
                "        return self.browse()"),
        "tags": "/stock_landed_cost_variance",
        "must_fail": ["test_component_landed_cost_after_the_finished_product_was_sold"],
    },
]
