import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Corrections recorded by the 19.0.2 adjustment mode are not rebuilt automatically.

    stock_landed_cost_variance 19.0.2 already marks every row it did not create as ``legacy``, and
    readers ignore legacy rows, so those corrections no longer show.  Folding them into the stored
    values during the upgrade would change the valuation of past periods, with no journal entry and
    without anyone asking: exactly the surprise the design rules out.  The products are listed so the
    rebuild wizard can be run on them deliberately, with a date chosen by the accountant.
    """
    cr.execute("""
        SELECT v.company_id, sm.product_id, COUNT(*)
          FROM stock_value_variance v
          JOIN stock_move sm ON sm.id = v.move_id
         WHERE v.origin = 'recalc' AND v.kind = 'legacy'
         GROUP BY v.company_id, sm.product_id
    """)
    rows = cr.fetchall()
    if rows:
        _logger.warning(
            "stock_valuation_avco_recalc 19.0.3: %s products carry corrections of the retired adjustment "
            "mode (now ignored). Run Rebuild Stock Valuation on them: %s",
            len(rows), ", ".join(f"company {c} product {p} ({n} rows)" for c, p, n in rows[:200]))
