"""Conservative migration: the three transfer fields moved from stock.picking
to stock.move.  Copy any populated picking value onto that picking's *recent*
moves and flag manual_override=True (conserve > lose).

Two hardening decisions for very large databases (Huarcaya has ~1M moves):

* RAW SQL, not the ORM.  An ORM write would fire the SUNAT ``@api.constrains``
  (<=20 chars / positive) on legacy data that may violate it (long foreign
  vendor document numbers on import companies) and roll back the whole upgrade
  - and, since the new stock.move columns are created in the same transaction,
  they would never come to exist.

* DATE-BOUNDED.  Old periods were already filed with the old data, so only
  moves from the last N months need the value on stock.move; older ones keep
  the value on the picking (legacy fields) and fall back to native in the
  report.  This keeps the migration cheap on huge datasets.  N defaults to 12
  and is overridable BEFORE the upgrade via the system parameter
  ``invoice_type_document_extension.migration_months`` (0 or negative = copy
  every move, no date limit).

A savepoint guarantees this archival copy can never abort the upgrade.
"""

import logging

_logger = logging.getLogger(__name__)

DEFAULT_MONTHS = 9


def _cutoff_months(cr):
    try:
        cr.execute(
            "SELECT value FROM ir_config_parameter WHERE key = %s",
            ('invoice_type_document_extension.migration_months',),
        )
        row = cr.fetchone()
        if row and row[0] is not None:
            raw = str(row[0]).strip()
            if raw.lstrip('-').isdigit():
                return int(raw)
    except Exception:  # noqa: BLE001 - fall back to the default on any issue
        pass
    return DEFAULT_MONTHS


def migrate(cr, version):
    # Old picking columns survive as orphans (Odoo never DROPs them).
    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'stock_picking'
          AND column_name = 'transfer_document_type_id'
    """)
    if not cr.fetchone():
        # Fresh install (no legacy columns) - nothing to copy.
        return

    months = _cutoff_months(cr)
    if months > 0:
        date_clause = " AND sm.date >= (CURRENT_DATE - make_interval(months => %s))"
        date_params = (months,)
    else:
        date_clause = ""
        date_params = ()

    try:
        with cr.savepoint(flush=False):
            # serie / number / manual_override: no FK -> always safe.
            cr.execute(f"""
                UPDATE stock_move sm
                   SET serie_transfer_document = sp.serie_transfer_document,
                       number_transfer_document = sp.number_transfer_document,
                       manual_override = TRUE
                  FROM stock_picking sp
                 WHERE sm.picking_id = sp.id
                   AND (sp.serie_transfer_document IS NOT NULL
                        OR sp.number_transfer_document IS NOT NULL)
                   {date_clause}
            """, date_params)
            copied_values = cr.rowcount

            # Document type only when the referenced type still exists (FK-safe).
            cr.execute(f"""
                UPDATE stock_move sm
                   SET transfer_document_type_id = sp.transfer_document_type_id,
                       manual_override = TRUE
                  FROM stock_picking sp
                 WHERE sm.picking_id = sp.id
                   AND sp.transfer_document_type_id IS NOT NULL
                   AND EXISTS (
                       SELECT 1 FROM l10n_latam_document_type t
                        WHERE t.id = sp.transfer_document_type_id
                   )
                   {date_clause}
            """, date_params)
            copied_types = cr.rowcount

        _logger.info(
            "invoice_type_document_extension migration: copied legacy transfer "
            "document to moves within the last %s months (%s serie/number rows, "
            "%s type rows).",
            months if months > 0 else 'ALL', copied_values, copied_types,
        )
    except Exception:  # noqa: BLE001 - never abort the upgrade over an archival copy
        _logger.exception(
            "invoice_type_document_extension migration: could not copy legacy "
            "picking transfer documents to moves; the historical values remain "
            "on the picking (legacy fields). Upgrade continues."
        )
