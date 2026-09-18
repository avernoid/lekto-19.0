"""19.0.1.0.0 -> 19.0.2.0.0 (design v4, section 4.6).

Rows of 19.0.1 held a correction computed with a FIFO-stack split (wrong for average cost with several
receipts, measured) and never folded into the stored value. The engine of 19.0.2 folds corrections at
the event instead, so those rows are kept as history only: kind ``legacy``, excluded from every ledger.

Reclassification entries already posted by 19.0.1 (``variance_move_id``) are kept and NOT reversed: an
automatic reversal would move accounting without the accountant seeing it. They stay listed for review.
To bring the stored values of those products in line, run the valuation rebuild wizard.
"""


def migrate(cr, version):
    cr.execute("""
        UPDATE stock_value_variance
           SET kind = 'legacy', absorbed = TRUE
         WHERE revaluation_id IS NULL
    """)
