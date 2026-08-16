"""Install-time bulk seeding of the Kardex stored columns.

The columns are pre-created in ``StockMove._auto_init`` so Odoo skips its eager,
per-record ORM recomputation at install (which OOMs / hangs the worker on a
production-sized ``stock_move``). Here we fill the historical values in one
set-based SQL pass -- batched by id range so each statement stays bounded on
very large tables -- reproducing ``_compute_kardex_qty`` byte for byte.
"""

# Batch width (in stock_move.id units). Big enough that even a sparse table is a
# handful of statements, small enough that a single UPDATE never spans millions
# of rows at once.
BATCH_SIZE = 100000

# UoM: plain related to the product's reference UoM (product_id.uom_id, which
# lives on product_template through product.product's delegation inheritance).
_SEED_UOM_SQL = """
    UPDATE stock_move sm
       SET kardex_uom_id = pt.uom_id
      FROM product_product pp
      JOIN product_template pt ON pt.id = pp.product_tmpl_id
     WHERE pp.id = sm.product_id
       AND sm.id BETWEEN %(lo)s AND %(hi)s
"""

# Qty step 1: default every move in the range to 0.0 (non-done moves, internal
# transfers, dropship and valued moves with no qualifying line all stay 0.0 --
# exactly what _compute_kardex_qty returns for them).
_SEED_QTY_ZERO_SQL = """
    UPDATE stock_move
       SET kardex_qty = 0.0
     WHERE id BETWEEN %(lo)s AND %(hi)s
"""

# Qty step 2: overwrite the valued in/out moves with the signed valued quantity.
#
# Faithful to stock_account's _get_valued_qty / _get_in_move_lines /
# _get_out_move_lines and to _compute_kardex_qty:
#   * only ``done`` moves flagged is_in / is_out;
#   * a line counts only if picked and not excluded for valuation
#     (owner unset, or owner == the company partner -- i.e. not consignment);
#   * an INCOMING line flips a NON-valued source into a valued destination,
#     an OUTGOING line flips a valued source into a NON-valued destination,
#     where "valued" == location has a company and usage in (internal, transit);
#   * is_in takes precedence over is_out (mirrors the ``elif`` in the compute),
#     hence ``NOT m.is_in`` on the outgoing branch;
#   * sign is +qty for incoming, -qty for outgoing; quantity is summed in the
#     product reference UoM (quantity_product_uom).
_SEED_QTY_VALUED_SQL = """
    UPDATE stock_move sm
       SET kardex_qty = agg.q
      FROM (
        SELECT ml.move_id AS move_id,
               (CASE WHEN m.is_in THEN 1.0 ELSE -1.0 END)
               * SUM(ml.quantity_product_uom) AS q
          FROM stock_move_line ml
          JOIN stock_move m         ON m.id = ml.move_id
          JOIN stock_location src   ON src.id = ml.location_id
          JOIN stock_location dst   ON dst.id = ml.location_dest_id
          LEFT JOIN res_company comp ON comp.id = ml.company_id
         WHERE ml.move_id BETWEEN %(lo)s AND %(hi)s
           AND m.state = 'done'
           AND ml.picked = TRUE
           AND (ml.owner_id IS NULL OR ml.owner_id = comp.partner_id)
           AND (
                (m.is_in
                 AND NOT (src.company_id IS NOT NULL AND src.usage IN ('internal', 'transit'))
                 AND (dst.company_id IS NOT NULL AND dst.usage IN ('internal', 'transit')))
             OR (m.is_out AND NOT m.is_in
                 AND (src.company_id IS NOT NULL AND src.usage IN ('internal', 'transit'))
                 AND NOT (dst.company_id IS NOT NULL AND dst.usage IN ('internal', 'transit')))
           )
         GROUP BY ml.move_id, m.is_in
      ) agg
     WHERE sm.id = agg.move_id
"""

# Value: sign the native (unsigned) ``value`` column, faithful byte-for-byte to
# ``_compute_kardex_value``. Trivial next to the qty seed -- no joins to
# move_line / location -- because ``value``, ``is_in`` and ``is_out`` are all
# stored columns already sitting on ``stock_move``. ``is_in`` takes precedence
# over ``is_out`` (the ``NOT is_in`` on the outgoing branch mirrors the compute's
# ``elif``); everything else (non-done, internal, dropship) stays 0.0.
_SEED_VALUE_SQL = """
    UPDATE stock_move
       SET kardex_value = CASE
            WHEN state = 'done' AND is_in            THEN value
            WHEN state = 'done' AND is_out AND NOT is_in THEN -value
            ELSE 0.0
       END + COALESCE(kardex_value_adjustment, 0.0)
     WHERE id BETWEEN %(lo)s AND %(hi)s
"""

# The adjustment column defaults to zero: a revaluation is only ever recorded
# going forward, so no historical move carries one. Seeded explicitly all the
# same, because _SEED_VALUE_SQL adds it and a NULL would poison the sum.
_SEED_ADJUSTMENT_ZERO_SQL = """
    UPDATE stock_move
       SET kardex_value_adjustment = 0.0,
           kardex_adjusted_qty = 0.0
     WHERE id BETWEEN %(lo)s AND %(hi)s
       AND (kardex_value_adjustment IS NULL OR kardex_adjusted_qty IS NULL)
"""


def _seed_kardex_columns(env, batch_size=BATCH_SIZE):
    """Populate kardex_qty / kardex_uom_id for existing moves via batched SQL.

    Idempotent and safe to re-run: every move in each id range is rewritten from
    scratch (zeroed, then valued moves overwritten). Returns the number of moves
    covered so callers/tests can assert it ran.
    """
    cr = env.cr
    cr.execute("SELECT MIN(id), MAX(id) FROM stock_move")
    min_id, max_id = cr.fetchone()
    if not max_id:
        return 0  # empty table (fresh / test DB before any move): nothing to do

    lo = min_id
    while lo <= max_id:
        params = {"lo": lo, "hi": lo + batch_size - 1}
        cr.execute(_SEED_UOM_SQL, params)
        cr.execute(_SEED_QTY_ZERO_SQL, params)
        cr.execute(_SEED_QTY_VALUED_SQL, params)
        cr.execute(_SEED_ADJUSTMENT_ZERO_SQL, params)
        cr.execute(_SEED_VALUE_SQL, params)
        lo += batch_size
    return max_id - min_id + 1


def _seed_kardex_value_column(env, batch_size=BATCH_SIZE):
    """Populate ONLY ``kardex_value`` via the same batched, set-based SQL.

    Used by the upgrade migration (``migrations/19.0.3.0.0/post-migrate.py``):
    ``post_init_hook`` runs only on a *fresh install*, so when an existing --
    possibly production-sized -- DB upgrades to the version that adds
    ``kardex_value``, the column is created empty by ``_auto_init`` (which
    deliberately suppresses Odoo's eager per-record recompute to avoid OOM on
    millions of moves) and nothing else fills it. This seeds it just as cheaply
    as install does. Idempotent; qty / uom are left untouched (already seeded on
    their own install). Returns the number of moves covered.
    """
    cr = env.cr
    cr.execute("SELECT MIN(id), MAX(id) FROM stock_move")
    min_id, max_id = cr.fetchone()
    if not max_id:
        return 0  # empty table: nothing to do
    lo = min_id
    while lo <= max_id:
        params = {"lo": lo, "hi": lo + batch_size - 1}
        cr.execute(_SEED_ADJUSTMENT_ZERO_SQL, params)
        cr.execute(_SEED_VALUE_SQL, params)
        lo += batch_size
    return max_id - min_id + 1


def post_init_hook(env):
    """Seed the Kardex columns for the pre-existing move history at install."""
    _seed_kardex_columns(env)
