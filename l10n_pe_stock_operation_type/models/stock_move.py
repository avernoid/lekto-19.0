from collections import defaultdict

from odoo import fields, models
from odoo.tools import config

# SUNAT Table 12 ("Tipo de Operacion") -- DUPLICATED on purpose from
# l10n_pe_reports_stock's picking field: this capture module must NOT depend on
# the PLE reports module (it is the Peru capture layer, symmetric to the LatAm
# document capture).  The catalogue is a legal constant that virtually never
# changes; a divergence would surface in tests.  Codes match the native ones
# verbatim so the bridge injection yields byte-identical 2-digit codes.
L10N_PE_OPERATION_TYPE_SELECTION = [
    ('1', 'National Sale'),
    ('2', 'National Purchase'),
    ('3', 'Consignation Received'),
    ('4', 'Consignation Delivered'),
    ('5', 'Return Received'),
    ('6', 'Return Delivered'),
    ('7', 'Bonus'),
    ('8', 'Prize'),
    ('9', 'Donation'),
    ('10', 'Production Output'),
    ('11', 'Transfer Between Warehouses'),
    ('12', 'Withdrawal'),
    ('13', 'Shrinkage'),
    ('14', 'Deterioration'),
    ('15', 'Destruction'),
    ('16', 'Opening Balance'),
    ('17', 'Export'),
    ('18', 'Import'),
    ('19', 'Production Entry'),
    ('20', 'Return from Production'),
    ('21', 'Transfer Entry Between Warehouses'),
    ('22', 'Entry for Misidentification'),
    ('23', 'Output for Misidentification'),
    ('24', 'Entry from Customer Return'),
    ('25', 'Return to Supplier'),
    ('26', 'Entry for Production Service'),
    ('27', 'Output for Production Service'),
    ('28', 'Adjustment for Inventory Difference'),
    ('29', 'Loan Goods Entry'),
    ('30', 'Loan Goods Exit'),
    ('31', 'Custody Goods Entry'),
    ('32', 'Custody Goods Exit'),
    ('33', 'Medical Samples'),
    ('34', 'Advertising'),
    ('35', 'Representation Expenses'),
    ('36', 'Withdrawal for Workers Delivery'),
    ('37', 'Collective Agreement Withdrawal'),
    ('38', 'Withdrawal for Replacement of Damaged Goods'),
    ('91', 'Others 1'),
    ('92', 'Others 2'),
    ('93', 'Others 3'),
    ('94', 'Others 4'),
    ('95', 'Others 5'),
    ('96', 'Others 6'),
    ('97', 'Others 7'),
    ('98', 'Others 8'),
    ('99', 'Others'),
]

# Mass/historic operations run per-move; on very large selections they are
# chunked with commits between batches (mirror of the sibling capture module).
_L10N_PE_OP_BATCH_SIZE = 1000


class StockMove(models.Model):
    """SUNAT Table-12 operation type captured at the *movement* level.

    The native l10n_pe_reports_stock field lives on stock.picking, forcing all
    moves of a transfer to share one type and unable to classify picking-less
    moves (inventory adjustments, scrap, MRP).  The PLE line is per stock.move,
    so this is the report's natural grain.  The bridge module reads this field
    (with a soft guard) and, when set, it wins over the picking-derived value.
    """

    _inherit = "stock.move"

    l10n_pe_operation_type = fields.Selection(
        selection=L10N_PE_OPERATION_TYPE_SELECTION,
        string="Type of Operation (PE)",
        copy=False,
        index="btree_not_null",
        help="SUNAT Table 12 operation type for this movement, used by the "
             "Peruvian Kardex PLE (12.1/13.1). If set, it overrides the "
             "picking-derived value in the PLE; if left blank, the PLE keeps "
             "its native behaviour.",
    )
    l10n_pe_operation_type_manual = fields.Boolean(
        string="Operation Type Manually Set",
        default=False,
        copy=False,
        help="Set automatically when a user (or the 'fixed'/'from picking' mass "
             "assignment) sets the operation type by hand. Automatic "
             "inference never overwrites a move flagged this way.",
    )

    # ------------------------------------------------------------------
    # Provenance gate: any write that touches the operation type WITHOUT the
    # l10n_pe_op_auto context flag is a human edit -> flag it manual.  Every
    # programmatic auto-writer passes l10n_pe_op_auto=True and never trips this.
    # ------------------------------------------------------------------
    def write(self, vals):
        if (
            "l10n_pe_operation_type" in vals
            and not self.env.context.get("l10n_pe_op_auto")
            and "l10n_pe_operation_type_manual" not in vals
        ):
            vals = dict(vals, l10n_pe_operation_type_manual=True)
        return super().write(vals)

    # ------------------------------------------------------------------
    # Heuristic inference from native stock/sale/purchase/mrp signals only
    # (never the picking's SUNAT field).  Returns a Table-12 code or False.
    # ------------------------------------------------------------------
    def _l10n_pe_infer_operation_type(self):
        self.ensure_one()
        fields_ = self._fields
        # Production (MRP): entry '19' / output '27' (mirrors the native PLE
        # mrp fallback in l10n_pe_reports_stock).
        is_mrp = self.picking_type_id.code == "mrp_operation" or (
            "production_id" in fields_ and self.production_id
        ) or (
            "raw_material_production_id" in fields_ and self.raw_material_production_id
        )
        if is_mrp:
            return "19" if self.is_in else "27"
        # Scrap -> shrinkage.
        if "scrap_id" in fields_ and self.scrap_id:
            return "13"
        # Sale delivery / customer return.
        if "sale_line_id" in fields_ and self.sale_line_id:
            return "1"
        # Purchase receipt / vendor return.
        if "purchase_line_id" in fields_ and self.purchase_line_id:
            return "2"
        # Inventory adjustment.
        if "inventory" in (self.location_id.usage, self.location_dest_id.usage):
            return "28"
        # Fall back to the same base mapping the native picking compute uses.
        return {"outgoing": "1", "incoming": "2", "internal": "21"}.get(
            self.picking_type_id.code
        )

    # ------------------------------------------------------------------
    # Auto engine (heuristic).  Buckets moves by inferred code so the number of
    # writes is O(distinct codes), not O(moves).  Anti-empty: never clears a
    # value with an inference that came back False.
    # ------------------------------------------------------------------
    def _l10n_pe_populate_operation_type(self, force=False, force_manual=False):
        buckets = defaultdict(list)
        for move in self:
            if move.company_id.country_code != "PE":
                continue
            if move.l10n_pe_operation_type_manual and not force_manual:
                continue
            if move.l10n_pe_operation_type and not (force or force_manual):
                continue
            code = move._l10n_pe_infer_operation_type()
            if not code:
                continue
            buckets[code].append(move.id)
        Move = self.env["stock.move"]
        for code, ids in buckets.items():
            Move.browse(ids).with_context(l10n_pe_op_auto=True).write({
                "l10n_pe_operation_type": code,
            })

    # ------------------------------------------------------------------
    # Policy filter shared by the mass wizard (fixed / from-picking sources).
    # ------------------------------------------------------------------
    def _l10n_pe_op_policy_filter(self, policy):
        if policy == "only_empty":
            return self.filtered(lambda m: not m.l10n_pe_operation_type)
        if policy == "overwrite_auto":
            return self.filtered(lambda m: not m.l10n_pe_operation_type_manual)
        return self  # overwrite_all

    # ------------------------------------------------------------------
    # Unified apply for the mass wizard: source (auto/fixed/from_picking) x
    # policy (only_empty/overwrite_auto/overwrite_all).  fixed/from_picking are
    # deliberate -> written WITHOUT the auto context so the gate stamps manual.
    # Batched with commits for very large selections (skipped under tests).
    # ------------------------------------------------------------------
    def _l10n_pe_apply_operation_type(self, source, policy, fixed_code=None):
        ids = self.ids
        multi_chunk = len(ids) > _L10N_PE_OP_BATCH_SIZE
        Move = self.env["stock.move"]
        picking_field = "l10n_pe_operation_type" in self.env["stock.picking"]._fields
        for offset in range(0, len(ids), _L10N_PE_OP_BATCH_SIZE):
            chunk = Move.browse(ids[offset:offset + _L10N_PE_OP_BATCH_SIZE])
            moves = chunk._l10n_pe_op_policy_filter(policy)
            if source == "auto":
                moves._l10n_pe_populate_operation_type(
                    force=policy in ("overwrite_auto", "overwrite_all"),
                    force_manual=policy == "overwrite_all",
                )
            else:
                buckets = defaultdict(list)
                for move in moves:
                    if move.company_id.country_code != "PE":
                        continue
                    if source == "fixed":
                        code = fixed_code
                    elif picking_field:  # from_picking
                        code = move.picking_id.l10n_pe_operation_type
                    else:
                        code = False
                    if not code:
                        continue
                    buckets[code].append(move.id)
                for code, bucket_ids in buckets.items():
                    # No auto context -> the write() gate stamps manual=True.
                    Move.browse(bucket_ids).write({"l10n_pe_operation_type": code})
            if multi_chunk:
                if not config["test_enable"]:
                    self.env.cr.commit()  # batch checkpoint (forbidden under tests)
                self.env.invalidate_all()

    # ------------------------------------------------------------------
    # Event: moves really became done -> infer the operation type for the empty,
    # non-manual ones (own autocompletion logic).
    # ------------------------------------------------------------------
    def _action_done(self, cancel_backorder=False):
        moves = super()._action_done(cancel_backorder=cancel_backorder)
        if moves:
            moves._l10n_pe_populate_operation_type()
        return moves
