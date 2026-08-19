from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command

from ..models.stock_move import STAGGER_STEP


class StockMoveDateAdjustWizard(models.TransientModel):
    _name = "stock.move.date.adjust.wizard"
    _description = "Regularise Stock Movement Dates"

    move_ids = fields.Many2many(
        "stock.move", string="Movements", required=True,
        help="Movements this regularisation will apply to. They are resolved from "
             "whatever you selected: a transfer, a scrap, a manufacturing order or "
             "the movements themselves.",
    )
    move_count = fields.Integer(
        string="Movement Count", compute="_compute_move_count",
        help="How many movements are about to be re-dated.",
    )
    document_count = fields.Integer(
        string="Document Count", compute="_compute_move_count",
        help="How many distinct source documents those movements belong to.",
    )
    scope_summary = fields.Char(
        string="Scope", compute="_compute_move_count",
        help="One-line recap of how many movements and documents the regularisation "
             "covers.",
    )

    mode = fields.Selection(
        [("fixed", "Fixed date"), ("shift", "Shift by an offset")],
        string="Mode", default="fixed", required=True,
        help="Fixed date sends every movement to the same instant. Shift moves the "
             "whole batch by an offset, which preserves the spacing the movements "
             "already had between them.",
    )
    new_date = fields.Datetime(
        string="New Date",
        help="Target date and time in Fixed date mode. Every selected movement lands "
             "here, except when staggering separates the phases of a document.",
    )
    stagger = fields.Boolean(
        string="Stagger within each document", default=True,
        help="Separate the phases of a same document by one hour, so a consumption "
             "never lands at the very same second as the output it feeds. Turn it off "
             "to collapse every movement of the document onto a single instant.",
    )
    shift_from = fields.Datetime(
        string="Move This Date",
        help="These two fields are a reference pair, not a range: the movements do "
             "not travel from one to the other. Pick a date you know -- usually the "
             "date the movements carry now -- and in the next field the date it "
             "should have been. Only the gap between the two is applied.",
    )
    shift_to = fields.Datetime(
        string="To This Date",
        help="Where the reference date should have landed. The gap between the two "
             "fields is added to every selected movement, so the spacing they "
             "already had between them is preserved. Example: Aug 17 to Jul 17 "
             "moves everything 31 days earlier, whatever dates the movements have.",
    )
    shift_summary = fields.Char(
        string="Resulting Shift", compute="_compute_shift_summary",
        help="What the reference pair actually does to every selected movement, "
             "spelled out so you can check it before applying.",
    )

    reason = fields.Char(
        string="Reason", required=True,
        help="Why this correction is being made. It is mandatory and it is kept in "
             "the chatter note posted on each affected document.",
    )
    sync_document = fields.Boolean(
        string="Also update the document date", default=True,
        help="Aligns the source document's own date field -- a transfer's Date of "
             "Transfer, a scrap's Date -- with its movements. Documents that carry "
             "no date of their own are left untouched.",
    )
    adjust_accounting = fields.Boolean(
        string="Also re-date the valuation entry", default=False,
        help="Off by default. Odoo forbids writing the date of a posted entry, so "
             "ticking this resets the entry to draft, clears its number, writes the "
             "new date and posts it again. The entry therefore comes back with a NEW "
             "number in the target period and leaves a gap in the original one. "
             "Entries that are reconciled, hash-protected or sitting in a closed "
             "period are refused instead.",
    )
    accounting_count = fields.Integer(
        string="Valuation Entry Count", compute="_compute_accounting_count",
        help="How many of the selected movements have a valuation journal entry. "
             "Entries only exist for products valued in real time, and they always "
             "keep the date they were posted on: Odoo treats the date of a posted "
             "entry as unmodifiable and ties it to the journal sequence.",
    )

    effective_move_ids = fields.Many2many(
        "stock.move", "stock_move_date_adjust_effective_rel", "wizard_id", "move_id",
        string="Movements Actually Affected", compute="_compute_effective_move_ids",
        help="The selection plus the movements that syncing the document header "
             "would drag along anyway. Odoo propagates a header date back to every "
             "movement of its document, so they are included openly instead of "
             "moving unannounced.",
    )
    sibling_count = fields.Integer(
        string="Movements Added", compute="_compute_effective_move_ids",
        help="How many movements were added to the selection because they belong "
             "to a document you are re-dating.",
    )

    line_ids = fields.One2many(
        "stock.move.date.adjust.line", "wizard_id",
        string="Preview", compute="_compute_line_ids",
        help="One row per movement, grouped by origin, showing the date it has now "
             "and the date it will get.",
    )
    warning_html = fields.Html(
        string="Warnings", compute="_compute_warning_html", sanitize=False,
        help="Alerts worth reading before applying. They never block the operation.",
    )

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    @api.model
    def action_open(self, records):
        """Open the wizard on ``records``, whatever model they belong to."""
        if not records:
            raise UserError(self.env._("Select at least one record."))
        if not hasattr(records, "_date_adjust_get_moves"):
            raise UserError(self.env._(
                "Movement date regularisation is not available on %s.",
                records._description,
            ))
        moves = records._date_adjust_get_moves()
        if not moves:
            raise UserError(self.env._(
                "The selected records have no stock movements."
            ))
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Regularise Movement Dates"),
            "res_model": self._name,
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_move_ids": [Command.set(moves.ids)],
            },
        }

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if res.get("move_ids") or "move_ids" not in fields_list:
            return res
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids")
        if active_model and active_ids:
            records = self.env[active_model].browse(active_ids).exists()
            if hasattr(records, "_date_adjust_get_moves"):
                res["move_ids"] = [Command.set(records._date_adjust_get_moves().ids)]
        return res

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------

    @api.depends("move_ids", "sync_document")
    def _compute_effective_move_ids(self):
        for wizard in self:
            moves = wizard.move_ids
            if wizard.sync_document:
                moves |= moves._date_adjust_cascade_siblings()
            wizard.effective_move_ids = moves
            wizard.sibling_count = len(moves) - len(wizard.move_ids)

    @api.depends("effective_move_ids")
    def _compute_move_count(self):
        for wizard in self:
            wizard.move_count = len(wizard.effective_move_ids)
            # Distinct source DOCUMENTS, not distinct origin groups. A single
            # manufacturing order yields two groups -- components and finished
            # product -- and counting groups announced "2 documents" for one
            # order. Movements with no document of their own (an inventory
            # adjustment) count as zero documents rather than as one.
            wizard.document_count = len({
                document
                for move in wizard.effective_move_ids
                for document in [move._date_adjust_origin()[1]]
                if document
            })
            wizard.scope_summary = (
                self.env._(
                    "You are about to re-date %(moves)s movement(s) across "
                    "%(documents)s document(s).",
                    moves=wizard.move_count, documents=wizard.document_count,
                )
                if wizard.document_count
                else self.env._(
                    "You are about to re-date %(moves)s movement(s).",
                    moves=wizard.move_count,
                )
            )

    @api.depends("mode", "shift_from", "shift_to")
    def _compute_shift_summary(self):
        for wizard in self:
            if wizard.mode != "shift" or not (wizard.shift_from and wizard.shift_to):
                wizard.shift_summary = False
                continue
            delta = wizard.shift_to - wizard.shift_from
            total = int(delta.total_seconds())
            forward = total >= 0
            total = abs(total)
            days, rest = divmod(total, 86400)
            hours, rest = divmod(rest, 3600)
            minutes = rest // 60
            gap = self.env._(
                "%(days)s days %(hours)sh %(minutes)smin",
                days=days, hours=hours, minutes=minutes,
            )
            wizard.shift_summary = (
                self.env._("Every movement moves %(gap)s later.", gap=gap)
                if forward
                else self.env._("Every movement moves %(gap)s earlier.", gap=gap)
            )

    @api.depends("effective_move_ids")
    def _compute_accounting_count(self):
        has_entries = "account_move_id" in self.env["stock.move"]._fields
        for wizard in self:
            wizard.accounting_count = (
                len(wizard.effective_move_ids.filtered("account_move_id"))
                if has_entries else 0
            )

    @api.depends("effective_move_ids", "mode", "new_date", "shift_from", "shift_to",
                 "stagger")
    def _compute_line_ids(self):
        for wizard in self:
            targets = wizard._target_by_move()
            labels = self.env["stock.move"]._date_adjust_origin_labels()
            vals_list = []
            for move in wizard.effective_move_ids:
                origin, document = move._date_adjust_origin()
                vals_list.append({
                    "move_id": move.id,
                    "origin_label": labels.get(origin, origin),
                    "document_name": document.display_name if document else move.reference,
                    "product_id": move.product_id.id,
                    "current_date": move.date,
                    "target_date": targets.get(move) or False,
                    "move_state": move.state,
                })
            vals_list.sort(key=lambda v: (v["origin_label"], v["document_name"] or "",
                                          v["current_date"] or fields.Datetime.now()))
            wizard.line_ids = [Command.clear()] + [Command.create(v) for v in vals_list]

    @api.depends("effective_move_ids", "mode", "new_date", "shift_from", "shift_to",
                 "stagger", "adjust_accounting", "sibling_count")
    def _compute_warning_html(self):
        for wizard in self:
            wizard.warning_html = wizard._build_warnings()

    # ------------------------------------------------------------------
    # Target computation
    # ------------------------------------------------------------------

    def _target_by_move(self):
        """``{move: datetime}``. Empty while the inputs are incomplete."""
        self.ensure_one()
        moves = self.effective_move_ids
        if not moves:
            return {}

        if self.mode == "fixed":
            if not self.new_date:
                return {}
            if not self.stagger:
                return {move: self.new_date for move in moves}
            return {
                move: self.new_date + timedelta(
                    seconds=STAGGER_STEP * move._date_adjust_stagger_rank()
                )
                for move in moves
            }

        if not (self.shift_from and self.shift_to):
            return {}
        delta = self.shift_to - self.shift_from
        return {move: move.date + delta for move in moves}

    def _build_warnings(self):
        self.ensure_one()
        targets = self._target_by_move()
        if not targets:
            return False

        messages = []

        if self.sibling_count:
            messages.append(self.env._(
                "%(count)s more movement(s) were added to the list: they share a "
                "document with your selection, and Odoo re-dates every movement of "
                "a document when its header date changes. They are shown below and "
                "get the same traceability. Untick 'Also update the document date' "
                "to touch only what you picked.",
                count=self.sibling_count,
            ))

        # A movement landing before the movement that fed it silently breaks the
        # chronology of the chain, which is how a FIFO stack gets scrambled.
        broken = []
        for move in self.effective_move_ids:
            for origin in move.move_orig_ids:
                origin_date = targets.get(origin, origin.date)
                if origin_date and targets[move] < origin_date:
                    broken.append((move, origin))
                    break
        if broken:
            messages.append(self.env._(
                "%(count)s movement(s) would end up before their own origin movement "
                "(e.g. %(move)s before %(origin)s). The chronology of the chain would "
                "no longer hold.",
                count=len(broken), move=broken[0][0].display_name,
                origin=broken[0][1].reference or broken[0][1].display_name,
            ))

        # Future dates are refused on apply. Say so here instead of letting the
        # user discover it only after filling everything in.
        now = fields.Datetime.now()
        future = [m for m in self.effective_move_ids if targets[m] > now]
        if future:
            messages.append(self.env._(
                "%(count)s movement(s) would land in the future, which is refused. "
                "Check the direction of the shift: the target date must be in the "
                "past.",
                count=len(future),
            ))

        not_done = self.effective_move_ids.filtered(lambda m: m.state != "done")
        if not_done:
            messages.append(self.env._(
                "%(count)s movement(s) are not done. On those, the date is the "
                "*planned* date, not the effective one.",
                count=len(not_done),
            ))

        if self.accounting_count and not self.adjust_accounting:
            messages.append(self.env._(
                "%(count)s valuation journal entries will keep their current date, so "
                "the stock ledger and the general ledger will differ for those "
                "movements.",
                count=self.accounting_count,
            ))
        elif self.accounting_count:
            messages.append(self.env._(
                "%(count)s valuation journal entries will be reset to draft, "
                "RENUMBERED into the target period and posted again. That leaves a "
                "gap in the sequence of their original period. Reconciled, "
                "hash-protected or closed-period entries are refused.",
                count=self.accounting_count,
            ))

        if not messages:
            return False
        return "<ul>%s</ul>" % "".join("<li>%s</li>" % m for m in messages)

    # ------------------------------------------------------------------
    # Apply
    # ------------------------------------------------------------------

    def action_apply(self):
        self.ensure_one()
        targets = self._target_by_move()
        if not targets:
            raise UserError(self.env._("Fill in the target date first."))

        self.effective_move_ids._adjust_date(
            targets,
            reason=self.reason,
            sync_document=self.sync_document,
            adjust_accounting=self.adjust_accounting,
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": self.env._(
                    "%(count)s movements regularised.",
                    count=len(self.effective_move_ids)
                ),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }


class StockMoveDateAdjustLine(models.TransientModel):
    _name = "stock.move.date.adjust.line"
    _description = "Stock Movement Date Regularisation Preview Line"
    _order = "origin_label, document_name, current_date"

    wizard_id = fields.Many2one(
        "stock.move.date.adjust.wizard", ondelete="cascade", string="Wizard",
        help="The regularisation this preview row belongs to.",
    )
    move_id = fields.Many2one(
        "stock.move", string="Movement", readonly=True,
        help="The stock movement this row previews.",
    )
    origin_label = fields.Char(
        string="Origin", readonly=True,
        help="What produced the movement: a transfer, a scrap, an inventory "
             "adjustment, a manufacturing order or a disassembly.",
    )
    document_name = fields.Char(
        string="Document", readonly=True,
        help="The source document, or the movement reference when the origin has no "
             "document of its own.",
    )
    product_id = fields.Many2one(
        "product.product", string="Product", readonly=True,
        help="Product moved by this movement.",
    )
    current_date = fields.Datetime(
        string="Current Date", readonly=True,
        help="Date the movement carries right now.",
    )
    target_date = fields.Datetime(
        string="New Date", readonly=True,
        help="Date the movement will carry once you apply.",
    )
    move_state = fields.Char(
        string="Status", readonly=True,
        help="State of the movement. On anything other than Done the date is the "
             "planned date, not the effective one.",
    )
