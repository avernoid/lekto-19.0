from collections import defaultdict

from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_datetime

# Spacing applied between phases of a same document when staggering is on.
STAGGER_STEP = 3600  # seconds


class StockMove(models.Model):
    _inherit = "stock.move"

    # Both are plain columns on purpose: no compute, no depends, no default.
    # Installing on a large database only adds two nullable columns (O(1) in
    # PostgreSQL) and triggers no recomputation whatsoever.
    original_date = fields.Datetime(
        string="Original Date",
        readonly=True,
        copy=False,
        help="Date this movement had before the first regularisation. Written only "
             "once, so it always points at the value Odoo recorded when the movement "
             "was processed.",
    )
    date_adjusted = fields.Boolean(
        string="Date Regularised",
        readonly=True,
        copy=False,
        index="btree_not_null",
        help="The date of this movement was regularised at least once.",
    )

    # ------------------------------------------------------------------
    # Origin resolution
    # ------------------------------------------------------------------

    def _date_adjust_get_moves(self):
        """Movements to regularise when this record is the wizard's input.

        Every model usable as an entry point implements this. Here the record
        already is the movement.
        """
        return self

    def _date_adjust_origin(self):
        """Return ``(origin key, source document)`` for this movement.

        ``False`` as the document means the movement has no header to keep in
        sync. Extended by bridge modules; the most specific link wins, which is
        why scraps are tested before transfers (a scrap issued from a transfer
        carries both links).
        """
        self.ensure_one()
        if self.scrap_id:
            return "scrap", self.scrap_id
        if self.is_inventory:
            return "inventory", False
        if self.picking_id:
            return "picking", self.picking_id
        return "other", False

    @api.model
    def _date_adjust_origin_labels(self):
        return {
            "picking": self.env._("Transfer"),
            "scrap": self.env._("Scrap"),
            "inventory": self.env._("Inventory Adjustment"),
            "other": self.env._("Other"),
        }

    def _date_adjust_stagger_rank(self):
        """Phase of this movement inside its document, for staggering.

        Movements sharing a rank land on the same instant; a higher rank lands
        ``STAGGER_STEP`` seconds later. Documents with a single phase keep 0.
        """
        self.ensure_one()
        return 0

    def _date_adjust_group_key(self):
        """Key identifying the document a movement belongs to."""
        self.ensure_one()
        origin, document = self._date_adjust_origin()
        return origin, document

    def _date_adjust_cascade_siblings(self):
        """Movements that syncing the document header would drag along.

        Writing a header date is not a cosmetic act: Odoo propagates it back to
        every movement of the document (``stock_picking.py:1146-1147`` for a
        transfer, ``mrp_production.py:1024-1027`` for a manufacturing order).
        Those siblings therefore change date whether or not they were selected.

        The wizard adds them to the selection instead of letting them move
        behind the user's back, so they appear in the preview and get the same
        ``original_date`` trace as everything else.
        """
        siblings = self.browse()
        for move in self:
            origin, document = move._date_adjust_origin()
            if origin == "picking" and document.state == "done":
                siblings |= document.move_ids
        return siblings - self

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _date_adjust_check(self, target_by_move):
        self._date_adjust_check_future(target_by_move)
        self._date_adjust_check_window(target_by_move)
        self._date_adjust_check_lock_dates(target_by_move)

    def _date_adjust_check_future(self, target_by_move):
        now = fields.Datetime.now()
        offenders = [m for m in self if target_by_move[m] > now]
        if not offenders:
            return
        detail = "\n".join("- %s" % move.display_name for move in offenders[:10])
        raise UserError(self.env._(
            "A movement cannot be dated in the future.\n\n%(moves)s", moves=detail,
        ))

    def _date_adjust_check_window(self, target_by_move):
        offenders = []
        for move in self:
            max_days = move.company_id.stock_move_date_adjust_max_days
            if not max_days:
                continue
            delta = abs((target_by_move[move] - move.date).days)
            if delta > max_days:
                offenders.append(self.env._(
                    "- %(move)s: %(delta)s days, maximum %(max)s",
                    move=move.display_name, delta=delta, max=max_days,
                ))
        if not offenders:
            return
        raise UserError(self.env._(
            "The regularisation exceeds the maximum shift allowed by the company."
            "\n\n%(moves)s", moves="\n".join(offenders[:10]),
        ))

    def _date_adjust_check_lock_dates(self, target_by_move):
        """Refuse to date a movement into a closed accounting period.

        This runs even when the accounting entry is left untouched: the point is
        not the ledger but the tax filing. A stock ledger for a period already
        reported must not gain movements after the fact.

        Soft-guarded: without ``account`` installed there are no lock dates.
        """
        Company = self.env["res.company"]
        if not hasattr(Company, "_get_lock_date_violations"):
            return
        offenders = []
        for move in self:
            company = move.company_id.sudo()
            locks = company._get_lock_date_violations(
                target_by_move[move].date(),
                fiscalyear=True, sale=False, purchase=False, tax=False, hard=True,
            )
            if locks:
                offenders.append(
                    "- %s: %s" % (move.display_name, Company._format_lock_dates(locks))
                )
        if not offenders:
            return
        raise UserError(self.env._(
            "These movements would land in a closed accounting period:\n\n%(moves)s"
            "\n\nReopen the period or pick another date.",
            moves="\n".join(offenders[:10]),
        ))

    # ------------------------------------------------------------------
    # Apply
    # ------------------------------------------------------------------

    def _adjust_date(self, target_by_move, reason, sync_document=True,
                     adjust_accounting=False):
        """Regularise the date of ``self``.

        :param target_by_move: ``{stock.move record: datetime}``, one entry per
            record in ``self``.
        :param reason: mandatory free text, kept in the chatter note.
        :param sync_document: also align the source document's own date field.
        :param adjust_accounting: also re-date the valuation journal entry, by
            resetting it to draft, renumbering it and posting it again. Off by
            default; see ``_date_adjust_accounting``.
        """
        if not self:
            return
        if not (reason or "").strip():
            raise UserError(self.env._(
                "A reason is required to regularise movement dates."
            ))
        self._date_adjust_check(target_by_move)
        if adjust_accounting:
            # Validated up front so a blocked entry never leaves the movements
            # re-dated and the ledger behind.
            self._date_adjust_check_accounting(target_by_move)

        todo = self.filtered(lambda m: m.date != target_by_move[m])
        if not todo:
            return

        # The date each movement carries right now, for the chatter note. It is
        # not the same as ``original_date``: on a second regularisation the note
        # must say what it is actually replacing, not the very first value.
        previous_by_move = {move: move.date for move in todo}

        # Snapshot the pre-regularisation date, once and only once. Grouped by
        # current date so a large batch costs one write per distinct date
        # instead of one per movement.
        by_current = defaultdict(lambda: self.browse())
        for move in todo.filtered(lambda m: not m.original_date):
            by_current[move.date] |= move
        for current, moves in by_current.items():
            moves.write({"original_date": current})

        # The header first, the movements second. Writing a header date makes
        # Odoo cascade it onto every movement of the document, so doing it last
        # would overwrite the individual targets -- and silently flatten a
        # shift, which exists precisely to preserve the spacing between them.
        if sync_document:
            todo._date_adjust_sync_document(target_by_move)

        by_target = defaultdict(lambda: self.browse())
        for move in todo:
            by_target[target_by_move[move]] |= move
        for target, moves in by_target.items():
            moves.write({"date": target, "date_adjusted": True})

        if adjust_accounting:
            todo._date_adjust_accounting(target_by_move)
        todo._date_adjust_log(target_by_move, reason, previous_by_move)

    def _date_adjust_sync_document(self, target_by_move):
        """Align the source document's own date field with its movements.

        Extended by bridge modules. Documents with no date field of their own --
        inventory adjustments, disassemblies -- are deliberately left alone: the
        only date a disassembly carries is ``create_date``, an ORM audit field
        that must not be falsified.
        """
        targets_by_doc = defaultdict(list)
        for move in self:
            origin, document = move._date_adjust_origin()
            if document:
                targets_by_doc[(origin, document)].append(target_by_move[move])

        for (origin, document), targets in targets_by_doc.items():
            if origin == "picking" and document.state == "done":
                document.date_done = min(targets)
            elif origin == "scrap":
                document.date_done = min(targets)

    # ------------------------------------------------------------------
    # Valuation entry
    # ------------------------------------------------------------------

    def _date_adjust_entry_targets(self, target_by_move):
        """``{account.move: date}``. One entry may serve several movements; when
        their targets differ the earliest one wins."""
        by_entry = {}
        if "account_move_id" not in self._fields:
            return by_entry
        for move in self:
            entry = move.account_move_id
            if not entry:
                continue
            target = target_by_move[move].date()
            if entry not in by_entry or target < by_entry[entry]:
                by_entry[entry] = target
        return by_entry

    def _date_adjust_check_accounting(self, target_by_move):
        """Refuse every case where re-dating the entry would be unsafe.

        Odoo blocks a plain ``write`` of ``date`` on a posted entry, and its
        sequence guard blocks posting it under a number belonging to another
        period. The supported route is draft -> renumber -> post, which Odoo
        does allow -- including, as it turns out, on a **reconciled** entry. It
        does not protect us there, so we protect ourselves.
        """
        blocked = []
        for entry, target in self._date_adjust_entry_targets(target_by_move).items():
            entry = entry.sudo()
            if entry.date == target:
                continue
            if entry.state != "posted":
                blocked.append(self.env._(
                    "- %(entry)s: only a posted entry can be re-dated (it is %(state)s).",
                    entry=entry.display_name, state=entry.state,
                ))
                continue
            if entry.inalterable_hash:
                blocked.append(self.env._(
                    "- %(entry)s: protected by an inalterability hash.",
                    entry=entry.display_name,
                ))
            if getattr(entry, "need_cancel_request", False):
                blocked.append(self.env._(
                    "- %(entry)s: requires a cancellation request.",
                    entry=entry.display_name,
                ))
            if any(line.matched_debit_ids or line.matched_credit_ids
                   for line in entry.line_ids):
                blocked.append(self.env._(
                    "- %(entry)s: reconciled. Odoo would let it through and break "
                    "the reconciliation silently; unreconcile it first.",
                    entry=entry.display_name,
                ))
            # Unposting touches the ORIGINAL period, so both ends must be open.
            company = entry.company_id.sudo()
            if hasattr(company, "_get_lock_date_violations"):
                locks = company._get_lock_date_violations(
                    entry.date, fiscalyear=True, sale=False, purchase=False,
                    tax=False, hard=True,
                )
                if locks:
                    blocked.append(self.env._(
                        "- %(entry)s: its current period is closed (%(locks)s).",
                        entry=entry.display_name,
                        locks=self.env["res.company"]._format_lock_dates(locks),
                    ))
        if blocked:
            raise UserError(self.env._(
                "These valuation entries cannot be re-dated:\n\n%(entries)s\n\n"
                "Untick the accounting option, or resolve them in Accounting first.",
                entries="\n".join(blocked[:10]),
            ))

    def _date_adjust_accounting(self, target_by_move):
        """Move the valuation entry to the movement's new date.

        Draft, clear the sequence number, write the date, post again. Clearing
        the number is not optional: Odoo refuses to post an entry whose number
        belongs to a different period. The entry therefore comes back with a
        **new number in the target period** and leaves a gap in the original
        one -- an accounting consequence the wizard states up front.
        """
        for entry, target in self._date_adjust_entry_targets(target_by_move).items():
            entry = entry.sudo()
            if entry.date == target:
                continue
            old_name = entry.name
            entry.button_draft()
            entry.write({"name": "/", "date": target})
            entry.action_post()
            entry.message_post(body=self.env._(
                "Re-dated by a stock movement date regularisation. Previously "
                "%(old_name)s; renumbered because Odoo ties an entry's number to "
                "its period.", old_name=old_name,
            ))

    # ------------------------------------------------------------------
    # Trace
    # ------------------------------------------------------------------

    def _date_adjust_log_target(self):
        """Record whose chatter receives the note.

        Inventory adjustments and any origin without a document fall back to the
        product template, which is always a ``mail.thread``.
        """
        self.ensure_one()
        _origin, document = self._date_adjust_origin()
        if document and hasattr(document, "message_post"):
            return document
        return self.product_id.product_tmpl_id

    def _date_adjust_format_datetime(self, value):
        """Datetime as the reader expects it: their timezone, their locale."""
        return format_datetime(self.env, value) if value else ""

    def _date_adjust_log(self, target_by_move, reason, previous_by_move=None):
        previous_by_move = previous_by_move or {}
        by_target = defaultdict(lambda: self.browse())
        for move in self:
            by_target[move._date_adjust_log_target()] |= move

        header = self.env._("Movement dates regularised")
        reason_label = self.env._("Reason")
        col_product = self.env._("Product")
        col_before = self.env._("Before")
        col_after = self.env._("After")

        for record, moves in by_target.items():
            # Markup so the note renders as a table instead of showing its own
            # tags as text, and so every interpolated value is escaped: a product
            # name carrying "<" or "&" must not break the message.
            rows = Markup("").join(
                Markup("<tr><td>%s</td><td>%s</td><td>%s</td></tr>") % (
                    move.product_id.display_name,
                    move._date_adjust_format_datetime(
                        previous_by_move.get(move, move.original_date)),
                    move._date_adjust_format_datetime(target_by_move[move]),
                )
                for move in moves
            )
            record.message_post(body=Markup(
                "<p><b>%s</b><br/>%s: %s</p>"
                "<table class='table table-sm'>"
                "<tr><th>%s</th><th>%s</th><th>%s</th></tr>%s</table>"
            ) % (header, reason_label, reason, col_product, col_before,
                 col_after, rows))

    # ------------------------------------------------------------------
    # Restore
    # ------------------------------------------------------------------

    def action_restore_original_date(self):
        """Put back the pre-regularisation date."""
        restorable = self.filtered(lambda m: m.date_adjusted and m.original_date)
        if not restorable:
            raise UserError(self.env._(
                "None of the selected movements has an original date to restore."
            ))

        targets = {move: move.original_date for move in restorable}
        restorable._date_adjust_check(targets)

        by_target = defaultdict(lambda: self.browse())
        for move in restorable:
            by_target[move.original_date] |= move
        for target, moves in by_target.items():
            moves.write({
                "date": target, "date_adjusted": False, "original_date": False,
            })

        restorable._date_adjust_sync_document(targets)
        return True
