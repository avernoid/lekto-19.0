"""Pour the parked reclassification setup into the new company-dependent columns.

Reads the copies made by ``pre-migrate.py`` and writes, for every company the
account belongs to, the value that company was already using — because until
19.0.7.0.0 there was a single value and every company used it. So nothing changes
behaviour here: what was one global setup becomes the same setup, stated once per
company, which each of them can now diverge from.

The storage format is Odoo's own for company-dependent fields: a ``jsonb`` object
keyed by company id **as text**, with the raw value (``{"1": 29}`` for a many2one,
``{"1": "always"}`` for a selection). Verified against a live Odoo 19 database
rather than assumed.

Accounts shared between companies may end up with a value that now fails the
company consistency check — a journal of company A offered to company B. That is
the defect being fixed showing its tail: the setup was already wrong, it simply
could not be seen. It is migrated as it stands so nothing is silently dropped, and
the accountant is told about it the next time the account is saved.
"""

import logging

_logger = logging.getLogger(__name__)

LEGACY_SUFFIX = "_pre_19080"

# Column -> extra condition that skips values not worth carrying over.
COLUMNS = {
    # 'none' is the field default, which is also the company-dependent fallback:
    # writing it would only bloat the jsonb.
    "reclass_mirror_mode": "AND a2.{legacy} <> 'none'",
    "reclass_target_account_id": "",
    "reclass_counterpart_account_id": "",
    "reclass_mirror_journal_id": "",
}


def _column_type(cr, column):
    cr.execute(
        """
        SELECT data_type
          FROM information_schema.columns
         WHERE table_name = 'account_account'
           AND column_name = %s
        """,
        (column,),
    )
    row = cr.fetchone()
    return row[0] if row else None


def migrate(cr, version):
    if not version:
        return

    for column, extra_condition in COLUMNS.items():
        legacy = f"{column}{LEGACY_SUFFIX}"
        if _column_type(cr, legacy) is None:
            # pre-migrate found nothing to park for this one.
            continue
        if _column_type(cr, column) != "jsonb":
            # Odoo did not create the new column: do NOT drop the copy, or the
            # setup would be lost with no way back.
            _logger.error(
                "account_reclassification: %s is not a jsonb column after the "
                "update, leaving %s in place so the setup can be recovered by hand",
                column, legacy,
            )
            continue

        cr.execute(
            f"""
            UPDATE account_account a
               SET "{column}" = sub.value
              FROM (
                    SELECT rel.account_account_id AS account_id,
                           jsonb_object_agg(
                               rel.res_company_id::text,
                               to_jsonb(a2."{legacy}")
                           ) AS value
                      FROM account_account_res_company_rel rel
                      JOIN account_account a2 ON a2.id = rel.account_account_id
                     WHERE a2."{legacy}" IS NOT NULL
                           {extra_condition.format(legacy=f'"{legacy}"')}
                  GROUP BY rel.account_account_id
                   ) sub
             WHERE a.id = sub.account_id
            """
        )
        migrated = cr.rowcount
        cr.execute(f'ALTER TABLE account_account DROP COLUMN "{legacy}"')
        _logger.info(
            "account_reclassification: %s carried over to company-dependent "
            "storage for %s account(s)", column, migrated,
        )
