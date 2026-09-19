"""Preserve the reclassification setup across the move to company-dependent fields.

Up to 19.0.7.0.0 the four reclassification fields of ``account.account`` were plain
columns holding a single value for every company. From 19.0.8.0.0 they are
``company_dependent``, which Odoo stores as ``jsonb`` keyed by company id.

Odoo cannot turn an ``integer`` column into a ``jsonb`` one, so it would move the
old column aside and create an empty one: every account configured by the customer
would come back unconfigured, and their bills would post without their entry
without a word. This script parks the old values under a private name; the
post-migrate script pours them into the new columns and drops the copies.

Splitting it in two is what makes it safe: between the two scripts Odoo creates the
new columns, so neither of them has to guess how Odoo spells the new storage.
"""

LEGACY_SUFFIX = "_pre_19080"

COLUMNS = (
    "reclass_mirror_mode",
    "reclass_target_account_id",
    "reclass_counterpart_account_id",
    "reclass_mirror_journal_id",
)


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
        # Fresh install: there is nothing to carry over.
        return

    for column in COLUMNS:
        current_type = _column_type(cr, column)
        if current_type is None or current_type == "jsonb":
            # Never existed, or somebody already converted it: leave it alone.
            continue
        legacy = f"{column}{LEGACY_SUFFIX}"
        if _column_type(cr, legacy) is not None:
            # A previous interrupted run already parked this one.
            continue
        cr.execute(
            f'ALTER TABLE account_account RENAME COLUMN "{column}" TO "{legacy}"'
        )
