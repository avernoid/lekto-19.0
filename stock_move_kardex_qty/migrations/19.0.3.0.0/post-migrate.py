"""Upgrade seed for ``kardex_value`` (added in 19.0.3.0.0).

``post_init_hook`` runs only on a fresh install, so an existing DB upgrading to
this version would get the new ``kardex_value`` column created empty by
``_auto_init`` (which suppresses the eager per-record recompute so a
production-sized ``stock_move`` never OOMs) and nothing would fill the history.

This post-migration runs *after* ``_auto_init`` has created the column and fills
it with the same batched, set-based SQL used at install -- so the upgrade path is
just as performant on millions of moves. Idempotent and safe to re-run.
"""

from odoo import SUPERUSER_ID, api

from odoo.addons.stock_move_kardex_qty.hooks import _seed_kardex_value_column


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _seed_kardex_value_column(env)
