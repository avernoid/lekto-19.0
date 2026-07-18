from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockTransferDocumentManage(models.TransientModel):
    """Single guided entry point that replaces the three former mass actions
    (fill-empty / force / recover-legacy) on the stock.move list.

    It exposes the two real axes behind those actions -- *source of truth*
    (re-derive from the live invoice/guide vs. recover the value stored on the
    picking) and *overwrite level* (empty only / non-manual / including manual)
    -- and shows a dynamic banner that, over the actual selection, states how
    many movements would change and gives a worked example.  It adds NO business
    logic: ``action_apply`` only routes to methods that already live on
    ``stock.move`` (``_itde_mass_populate`` / ``action_itde_recover_legacy``).
    """

    _name = 'stock.transfer.document.manage'
    _description = 'Assign transfer document type & number on movements'

    move_ids = fields.Many2many(
        comodel_name='stock.move',
        string='Movements',
        help="Stock movements this wizard will act on (the current selection).",
    )
    strategy = fields.Selection(
        selection=[
            ('fill_empty', 'Fill empty only (safe)'),
            ('rederive', 'Re-derive from invoice / remission guide'),
            ('recover_legacy', 'Recover serie/number stored on the picking'),
        ],
        string='Action to perform',
        default='fill_empty',
        required=True,
        help="Fill empty: only movements with no document yet (safe, touches "
             "nothing already filled).\n"
             "Re-derive: recompute from each movement's invoice or remission "
             "guide and overwrite automatic values (manual ones stay protected "
             "unless you tick the box below).\n"
             "Recover from picking: copy the value older versions stored on the "
             "picking onto the selected movements.",
    )
    include_manual = fields.Boolean(
        string='Also overwrite manual edits',
        help="Re-derive and Recover modes. If enabled, also overwrite movements "
             "whose document was edited by hand. If disabled (default), manual "
             "movements are left untouched. Use with care: this replaces human "
             "edits.",
    )
    legacy_available = fields.Boolean(
        compute='_compute_legacy_available',
        help="Whether this database still has the legacy picking columns to "
             "recover from.",
    )

    # Live preview counts over the selection (non-stored, feed the banner).
    count_selected = fields.Integer(compute='_compute_counts')
    count_empty = fields.Integer(compute='_compute_counts')
    count_auto = fields.Integer(compute='_compute_counts')
    count_manual = fields.Integer(compute='_compute_counts')
    count_will_change = fields.Integer(compute='_compute_will_change')

    banner = fields.Html(
        compute='_compute_banner', sanitize=False,
        string='Effect',
    )

    # ------------------------------------------------------------------
    # Seed the selection from the list's active_ids.
    # ------------------------------------------------------------------
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('active_model') == 'stock.move':
            active_ids = self.env.context.get('active_ids')
            if active_ids:
                res['move_ids'] = [(6, 0, active_ids)]
        return res

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    def _compute_legacy_available(self):
        available = 'transfer_document_type_id' in self.env['stock.picking']._fields
        for wiz in self:
            wiz.legacy_available = available

    @api.depends('move_ids', 'move_ids.transfer_document_type_id',
                 'move_ids.manual_override')
    def _compute_counts(self):
        for wiz in self:
            moves = wiz.move_ids
            wiz.count_selected = len(moves)
            wiz.count_empty = len(
                moves.filtered(lambda m: not m.transfer_document_type_id))
            wiz.count_manual = len(moves.filtered('manual_override'))
            wiz.count_auto = len(moves.filtered(
                lambda m: m.transfer_document_type_id and not m.manual_override))

    @api.depends('move_ids', 'strategy', 'include_manual')
    def _compute_will_change(self):
        for wiz in self:
            wiz.count_will_change = len(wiz._affected_moves())

    @api.depends('move_ids', 'strategy', 'include_manual', 'legacy_available',
                 'count_selected', 'count_empty', 'count_auto', 'count_manual',
                 'count_will_change')
    def _compute_banner(self):
        for wiz in self:
            wiz.banner = wiz._build_banner()

    # ------------------------------------------------------------------
    # Which moves would actually change, per strategy (no writes) -- the honest
    # basis for count_will_change and "View affected movements".  Never promises
    # more than action_apply will do.
    # ------------------------------------------------------------------
    def _affected_moves(self):
        self.ensure_one()
        moves = self.move_ids
        if not moves:
            return moves
        if self.strategy == 'recover_legacy':
            # Upper bound: the SQL copy decides the real subset (which pickings
            # actually carry a legacy value); the banner labels this "up to".
            # Manual moves are protected unless include_manual (same axis as
            # rederive), so drop them from the estimate when not included.
            if not self.include_manual:
                moves = moves.filtered(lambda m: not m.manual_override)
            return moves
        if self.strategy == 'fill_empty':
            candidates = moves.filtered(
                lambda m: not m.manual_override and not m.transfer_document_type_id)
            return candidates.filtered(lambda m: m._itde_document_values())
        # rederive: re-derive and compare with the stored value (skip manuals
        # unless include_manual).  Mirrors _itde_suspect_ids, extended to
        # optionally include manual moves.
        result = self.env['stock.move']
        for move in moves:
            if move.manual_override and not self.include_manual:
                continue
            values = move._itde_document_values()
            if not values:
                continue
            _doc_type, serie, number = values
            if (serie != (move.serie_transfer_document or '')
                    or number != (move.number_transfer_document or '')):
                result |= move
        return result

    # ------------------------------------------------------------------
    # Dynamic banner
    # ------------------------------------------------------------------
    def _build_banner(self):
        self.ensure_one()
        # Line 1 -- always: the selection, with each category defined inline so
        # the counts are self-explanatory (no external legend needed).
        summary = _(
            "Of %(total)s selected movements: %(empty)s empty (no document "
            "yet) · %(auto)s automatic (filled by the system from the "
            "invoice/guide) · %(manual)s manual (edited by hand).",
            total=self.count_selected, empty=self.count_empty,
            auto=self.count_auto, manual=self.count_manual,
        )
        # Line 4 -- only for the derivation strategies: where the value comes
        # from, shown as a worked example.
        example = _(
            "Example: a movement with invoice F001-00001234 becomes Type 01 "
            "(Invoice) · Serie F001 · Correlativo 1234. With no invoice but a "
            "guide T001-000045 → Type 09 (Remission Guide) · Serie T001 · "
            "Correlativo 45.")
        show_example = self.strategy in ('fill_empty', 'rederive')
        caveat = ''
        if self.strategy == 'fill_empty':
            css = 'alert-success'
            effect = _(
                "%(n)s empty movements will be filled from their invoice or "
                "remission guide. Automatic and manual movements are left "
                "untouched.", n=self.count_will_change,
            )
            caveat = _(
                "Empty movements without a posted invoice or remission guide "
                "cannot be filled and stay empty, so this number can be lower "
                "than the empty count above.")
        elif self.strategy == 'rederive' and not self.include_manual:
            css = 'alert-warning'
            effect = _(
                "%(n)s movements will be re-derived from their invoice or guide "
                "(empty ones plus automatic ones whose value would change). The "
                "%(manual)s manual movements stay protected.",
                n=self.count_will_change, manual=self.count_manual,
            )
            caveat = _(
                "A re-derivation that comes back empty (e.g. the invoice is not "
                "posted) never wipes an existing value.")
        elif self.strategy == 'rederive':
            css = 'alert-danger'
            effect = _(
                "%(n)s movements will be re-derived from their invoice or guide, "
                "INCLUDING the %(manual)s manual ones — their hand-typed values "
                "will be replaced.",
                n=self.count_will_change, manual=self.count_manual,
            )
            caveat = _(
                "A re-derivation that comes back empty (e.g. the invoice is not "
                "posted) never wipes an existing value.")
        elif not self.legacy_available:
            css = 'alert-secondary'
            effect = _(
                "This database has no legacy picking columns; this option does "
                "not apply. Use “Re-derive” or “Fill empty” instead.")
        elif self.include_manual:
            css = 'alert-danger'
            effect = _(
                "The legacy document from the picking will be copied onto up to "
                "%(n)s movements, INCLUDING the %(manual)s manual ones — their "
                "hand-typed values will be replaced. Changed movements are "
                "flagged as manual.",
                n=self.count_will_change, manual=self.count_manual,
            )
            caveat = self._legacy_caveat()
        else:
            css = 'alert-warning'
            effect = _(
                "The legacy document from the picking will be copied onto up to "
                "%(n)s non-manual movements. The %(manual)s manual movements "
                "stay protected. Changed movements are flagged as manual.",
                n=self.count_will_change, manual=self.count_manual,
            )
            caveat = self._legacy_caveat()
        paragraphs = [
            Markup("<p class='mb-1'>{0}</p>").format(summary),
            Markup("<p class='mb-1'><strong>{0}</strong></p>").format(effect),
        ]
        for muted in (caveat, example if show_example else ''):
            if muted:
                paragraphs.append(
                    Markup("<p class='mb-0 text-muted'>{0}</p>").format(muted))
        body = Markup("").join(paragraphs)
        return Markup(
            "<div class='alert {0}' role='alert'>{1}</div>"
        ).format(css, body)

    def _legacy_caveat(self):
        return _(
            "'Legacy' is the document that older module versions saved on the "
            "transfer (picking); newer versions store it on each movement. "
            "'Up to' because only movements whose picking actually kept such a "
            "value change — the rest stay unchanged.")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_apply(self):
        self.ensure_one()
        if not self.move_ids:
            raise UserError(_("Select at least one movement."))
        if self.strategy == 'recover_legacy':
            if not self.legacy_available:
                raise UserError(_(
                    "This database has no legacy picking columns to recover "
                    "from."))
            self.move_ids.action_itde_recover_legacy(
                skip_manual=not self.include_manual)
        elif self.strategy == 'fill_empty':
            self.move_ids._itde_mass_populate(force=False)
        else:  # rederive
            self.move_ids._itde_mass_populate(
                force=True, force_manual=self.include_manual)
        return {'type': 'ir.actions.act_window_close'}

    def action_view_affected(self):
        """Open the exact movements the current choice would change, to audit
        before applying."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Affected movements"),
            'res_model': 'stock.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self._affected_moves().ids)],
            'target': 'current',
        }
