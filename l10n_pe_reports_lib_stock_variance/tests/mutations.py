"""Mutations of this module. See stock_landed_cost_variance/tests/mutations.py for the why."""

MUTATIONS = [
    {
        "name": "ple_37_known_value",
        "why": "the 3.7 prints today's value for a past period, and leaves out the last day",
        "file": "models/account_general_ledger.py",
        "old": '        date_to = fields.Date.to_date(options["date"]["date_to"])',
        "new": ("        return super()._l10n_pe_get_lib_3_7_data(options, currency_table_query)\n"
                '        date_to = fields.Date.to_date(options["date"]["date_to"])'),
        "tags": "/l10n_pe_reports_lib_stock_variance",
        "must_fail": ["test_a_past_period_keeps_the_value_it_was_filed_with",
                      "test_movements_of_the_last_day_are_included"],
    },
]
