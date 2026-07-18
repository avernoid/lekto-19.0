from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_pe_stock_operation_type.models.stock_move import (
    L10N_PE_OPERATION_TYPE_SELECTION,
)


class L10nPeOperationTypeAssign(models.TransientModel):
    """One mass action, one wizard: choose a SOURCE (from picking / a fixed
    value / the smart heuristic) x a POLICY (only empty / overwrite auto /
    overwrite all).  A single button in the Action menu instead of a cluster of
    them.  Launchable from a stock.move list or a stock.picking list (in the
    latter case it targets the moves of the selected transfers)."""

    _name = "l10n_pe.operation.type.assign"
    _description = "Assign SUNAT Operation Type on stock movements"

    source = fields.Selection(
        selection=[
            ("auto", "Automatic (infer from the movement)"),
            ("from_picking", "From the transfer (picking)"),
            ("fixed", "A fixed value"),
        ],
        string="Source",
        required=True,
        default="auto",
        help="Where the operation type comes from:\n"
             "- Automatic: inferred from the movement (sale, purchase, "
             "production, scrap, inventory adjustment...).\n"
             "- From the transfer: copies the SUNAT operation type set on the "
             "picking (requires the PLE stock reports module).\n"
             "- A fixed value: the SUNAT Table 12 code you pick below.",
    )
    policy = fields.Selection(
        selection=[
            ("only_empty", "Only movements without a type"),
            ("overwrite_auto", "Overwrite auto-filled (keep manual edits)"),
            ("overwrite_all", "Overwrite everything (including manual edits)"),
        ],
        string="Apply to",
        required=True,
        default="only_empty",
        help="Which of the selected movements are touched:\n"
             "- Only movements without a type: fills gaps, safest.\n"
             "- Overwrite auto-filled: re-derives, but respects values set by "
             "hand.\n"
             "- Overwrite everything: also replaces manual edits.",
    )
    operation_type = fields.Selection(
        selection=L10N_PE_OPERATION_TYPE_SELECTION,
        string="Operation Type",
        help="SUNAT Table 12 code to stamp on the selected movements. "
             "Examples: 07 Bonus = free promotional delivery; 13 Shrinkage = "
             "normal physical loss of the process; 28 Adjustment for Inventory "
             "Difference = result of a physical count.",
    )
    move_count = fields.Integer(string="Selected movements", readonly=True)
    eligible_count = fields.Integer(
        string="Will be assigned", compute="_compute_preview")
    manual_count = fields.Integer(
        string="Manually set", compute="_compute_preview")
    filled_count = fields.Integer(
        string="Already have a type", compute="_compute_preview")
    preview_hint = fields.Text(compute="_compute_preview")

    # ------------------------------------------------------------------
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        moves = self._get_target_moves()
        res["move_count"] = len(moves)
        return res

    def _get_target_moves(self):
        """Resolve the moves to act on from the launching context: a stock.move
        selection directly, or every move of the selected stock.pickings."""
        ctx = self.env.context
        active_model = ctx.get("active_model")
        active_ids = ctx.get("active_ids") or []
        if active_model == "stock.picking":
            return self.env["stock.picking"].browse(active_ids).move_ids
        if active_model == "stock.move":
            return self.env["stock.move"].browse(active_ids)
        return self.env["stock.move"]

    @api.depends("source", "policy", "operation_type")
    def _compute_preview(self):
        for wizard in self:
            moves = wizard._get_target_moves()
            pe_moves = moves.filtered(
                lambda m: m.company_id.country_code == "PE")
            eligible = pe_moves._l10n_pe_op_policy_filter(wizard.policy)
            wizard.manual_count = len(
                pe_moves.filtered("l10n_pe_operation_type_manual"))
            wizard.filled_count = len(
                pe_moves.filtered("l10n_pe_operation_type"))
            wizard.eligible_count = len(eligible)
            protected = wizard.manual_count if wizard.policy != "overwrite_all" else 0
            non_pe = len(moves) - len(pe_moves)
            parts = [
                _("%s movement(s) eligible under this policy.",
                  wizard.eligible_count),
            ]
            if protected:
                parts.append(_("%s manual movement(s) will be respected.",
                               protected))
            if non_pe:
                parts.append(_("%s non-Peruvian movement(s) are ignored.",
                               non_pe))
            if wizard.source == "auto":
                parts.append(_("Automatic inference skips movements it cannot "
                               "classify."))
            elif wizard.source == "from_picking":
                parts.append(_("Movements whose transfer has no operation type "
                               "are skipped."))
            wizard.preview_hint = " ".join(parts)

    # ------------------------------------------------------------------
    def action_apply(self):
        self.ensure_one()
        if self.source == "fixed" and not self.operation_type:
            raise UserError(_("Choose a SUNAT operation type to apply."))
        moves = self._get_target_moves()
        if not moves:
            raise UserError(_("No stock movements selected."))
        moves._l10n_pe_apply_operation_type(
            source=self.source,
            policy=self.policy,
            fixed_code=self.operation_type,
        )
        return {"type": "ir.actions.act_window_close"}
