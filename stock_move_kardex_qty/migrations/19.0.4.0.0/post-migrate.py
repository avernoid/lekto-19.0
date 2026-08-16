"""Seed the two Kardex adjustment columns on an existing database.

``post_init_hook`` only runs on a fresh install, so an existing -- possibly
production-sized -- database upgrading to the version that adds
``kardex_value_adjustment`` / ``kardex_adjusted_qty`` gets them created empty by
``_auto_init`` (which deliberately suppresses Odoo's eager per-record recompute
to avoid OOM on millions of moves) and nothing else fills them.

Both are seeded to zero, which is also their correct value: a revaluation is
only ever recorded going forward, so no historical move carries one.  That means
``kardex_value`` does not move on upgrade either -- an existing ledger reads
exactly as it did before.  Re-seeding it here anyway keeps the column and the
compute in step should a variance already exist (a re-run of the migration).
"""

from odoo.addons.stock_move_kardex_qty.hooks import _seed_kardex_value_column


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    _seed_kardex_value_column(env)
