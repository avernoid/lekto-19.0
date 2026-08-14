import logging

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    reclass_mirror_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Reclassification Entry",
        readonly=True,
        copy=False,
        ondelete="set null",
        index="btree_not_null",
        check_company=True,
        help="Separate journal entry holding the reclassification of this "
             "bill. It is created when the bill is posted, cancelled when the bill "
             "goes back to draft, and rebuilt from scratch on every regeneration, so "
             "there is never more than one active entry per bill.",
    )
    reclass_source_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Reclassified Bill",
        readonly=True,
        copy=False,
        ondelete="set null",
        index="btree_not_null",
        help="Vendor bill this reclassification entry was generated from. Set on the "
             "reclassification entry itself, it keeps the trail back to the source "
             "document even after the entry has been superseded and cancelled.",
    )
    reclass_mirror_applicable = fields.Boolean(
        string="Reclassification Applicable",
        compute="_compute_reclass_mirror_applicable",
        help="Technical field, not stored: True when at least one line of this bill is "
             "posted on an account configured to produce a reclassification entry. It only "
             "drives the visibility of the regeneration button.",
    )

    # -------------------------------------------------------------------------
    # COMPUTE
    # -------------------------------------------------------------------------

    @api.depends_context("company")
    @api.depends(
        "move_type",
        "journal_id.generate_reclass_mirror",
        "invoice_line_ids.balance",
        "invoice_line_ids.account_id.reclass_mirror_mode",
        "invoice_line_ids.account_id.reclass_target_account_id",
        "invoice_line_ids.account_id.reclass_counterpart_account_id",
    )
    def _compute_reclass_mirror_applicable(self):
        for move in self:
            move.reclass_mirror_applicable = bool(move._reclass_get_mirror_line_specs())

    # -------------------------------------------------------------------------
    # NATIVE OVERRIDES -- always super() first, the engine runs as a wrapper
    # -------------------------------------------------------------------------

    def _post(self, *args, **kwargs):
        # ``_post`` is the single funnel of every posting path (action_post, the
        # abnormal-amount confirmation wizard and the auto-post cron), so hooking it
        # covers them all. It returns the subset actually posted when soft=True.
        # The signature is left open on purpose: a future parameter must not turn
        # this wrapper into a TypeError on every posting.
        posted = super()._post(*args, **kwargs)
        posted._reclass_sync_mirror_moves()
        return posted

    def button_draft(self):
        res = super().button_draft()
        self._reclass_drop_mirror_moves()
        return res

    def unlink(self):
        self._reclass_drop_mirror_moves()
        return super().unlink()

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------

    def action_reclass_generate_mirror(self):
        """Manually (re)generate the reclassification entry of the selected bills.

        Single-record path (the button on the bill): anything that prevents the
        regeneration is raised, because the user aimed at this precise bill.
        """
        for move in self:
            if move.state != "posted":
                raise UserError(_(
                    "The reclassification entry can only be generated for a posted bill "
                    "(%(move)s is %(state)s).",
                    move=move.display_name, state=move.state,
                ))
            if move.move_type not in self._reclass_supported_move_types():
                raise UserError(_(
                    "The reclassification entry only applies to vendor bills and vendor "
                    "credit notes."
                ))
            move._reclass_generate_mirror_move(explain_when_not_applicable=True)
        return True

    def action_reclass_generate_mirror_batch(self):
        """Mass (re)generation from the list view, with the current setup.

        Whatever cannot be regenerated is skipped instead of aborting the whole
        batch: bills that are not posted, that are not vendor documents, that have
        no reclassification setup, and - deliberately - those whose date sits in a period
        locked by the native accounting rules. The result is reported as a
        notification so nothing is skipped silently.
        """
        generated = skipped = locked = 0
        for move in self:
            if (
                move.state != "posted"
                or move.move_type not in self._reclass_supported_move_types()
                or move.reclass_source_move_id
            ):
                skipped += 1
                continue
            if not move._reclass_is_lock_date_free():
                locked += 1
                continue
            if move._reclass_generate_mirror_move():
                generated += 1
            else:
                skipped += 1

        message = _("%(generated)s reclassification entries generated.", generated=generated)
        if skipped:
            message += _(" %(skipped)s bills skipped (not applicable).", skipped=skipped)
        if locked:
            message += _(
                " %(locked)s bills skipped: their period is locked.", locked=locked)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "warning" if locked else "success",
                "title": _("Reclassification Entries"),
                "message": message,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def action_reclass_open_mirror(self):
        self.ensure_one()
        if not self.reclass_mirror_move_id:
            raise UserError(_("This bill has no reclassification entry."))
        action = {
            "type": "ir.actions.act_window",
            "name": _("Reclassification Entry"),
            "res_model": "account.move",
            "res_id": self.reclass_mirror_move_id.id,
            "view_mode": "form",
        }
        form_view = self.env.ref("account.view_move_form", raise_if_not_found=False)
        if form_view:
            action["views"] = [(form_view.id, "form")]
        return action

    # -------------------------------------------------------------------------
    # ENGINE
    # -------------------------------------------------------------------------

    @api.model
    def _reclass_supported_move_types(self):
        """Move types the mirror engine applies to.

        Credit notes are included so a returned purchase reverses its own mirror
        entry; leaving them out would keep a 60/61 reclassification that the books
        no longer support.
        """
        return ("in_invoice", "in_refund")

    def _reclass_sync_mirror_moves(self):
        """Generate the reclassification entry of every supported bill of ``self``.

        Automatic path: best effort. Each mirror is built inside its own
        savepoint, so a broken reclassification setup (a target account of another company, a
        journal that cannot be used, an account made inactive...) can never roll
        back or block the posting of the bill itself. The failure is logged and
        the accountant can retry with the manual button, which does raise.
        """
        candidates = self.filtered(
            lambda m: m.move_type in m._reclass_supported_move_types()
            and m.state == "posted"
            and not m.reclass_source_move_id  # never mirror a mirror
        )
        for move in candidates:
            try:
                with self.env.cr.savepoint():
                    move._reclass_generate_mirror_move()
            except Exception:  # noqa: BLE001 - posting a bill must never fail here
                self.env.invalidate_all()
                _logger.exception(
                    "reclassification entry could not be generated for bill %s: the bill "
                    "is posted natively, use the manual button once the setup is "
                    "fixed", move.name,
                )

    def _reclass_get_mirror_journal(self, accounts=None):
        """Journal receiving the reclassification entry, or an empty recordset.

        Fallback chain, from the most specific to the most general:
        the account of the bill line -> the journal of the bill -> the company
        default. Nothing is guessed beyond that: without any of the three, no
        reclassification entry is generated.

        :param accounts: the ``account.account`` records being mirrored, whose own
            journal wins. When several of them define one, the first in chart order.
        """
        self.ensure_one()
        account_journals = (accounts or self.env["account.account"]).sorted(
            "code").mapped("reclass_mirror_journal_id")
        return (
            account_journals[:1]
            or self.journal_id.reclass_mirror_journal_id
            or self.company_id.reclass_mirror_journal_id
        )

    def _reclass_get_mirror_line_specs(self):
        """Describe the mirror lines to build for this move.

        A line is a candidate when its account is set to ``always``, or to
        ``journal`` while the journal of the bill has ``generate_reclass_mirror``
        ticked.

        The mirror accounts always come from the account setup: the production
        account of the product category belongs to the native stock flow, not to
        this purchase reclassification.

        :return: list of dicts ``{'line', 'target_account', 'counterpart_account',
                 'balance'}``
        """
        self.ensure_one()
        specs = []
        if self.move_type not in self._reclass_supported_move_types():
            return specs
        company_currency = self.company_id.currency_id
        journal_allows = self.journal_id.generate_reclass_mirror
        for line in self.invoice_line_ids.filtered(lambda l: l.display_type == "product"):
            account = line.account_id
            if account.reclass_mirror_mode == "none":
                continue
            if account.reclass_mirror_mode == "journal" and not journal_allows:
                continue
            if not account.reclass_target_account_id or not account.reclass_counterpart_account_id:
                continue
            if not company_currency or company_currency.is_zero(line.balance):
                continue
            specs.append({
                "line": line,
                "account": account,
                # The target keeps the side of the mirrored line (debit stays
                # debit, credit stays credit on a refund); the counterpart always
                # takes the opposite side, so the entry balances.
                "target_account": account.reclass_target_account_id,
                "counterpart_account": account.reclass_counterpart_account_id,
                # ``balance`` is already expressed in the company currency, so a
                # foreign-currency bill is converted by the native engine.
                "balance": line.balance,
            })
        return specs

    def _reclass_prepare_mirror_line_vals(self, spec, account, balance):
        source = spec["line"]
        return {
            "name": source.name or source.product_id.display_name or self.name,
            "account_id": account.id,
            "partner_id": self.partner_id.id,
            "product_id": source.product_id.id,
            "quantity": source.quantity,
            "currency_id": self.company_id.currency_id.id,
            "balance": balance,
            "amount_currency": balance,
            "analytic_distribution": source.analytic_distribution or False,
            "tax_ids": [Command.clear()],
            "tax_tag_ids": [Command.clear()],
        }

    def _reclass_prepare_mirror_move_vals(self, journal, specs):
        line_vals = []
        for spec in specs:
            line_vals.append(Command.create(
                self._reclass_prepare_mirror_line_vals(
                    spec, spec["target_account"], spec["balance"])
            ))
            line_vals.append(Command.create(
                self._reclass_prepare_mirror_line_vals(
                    spec, spec["counterpart_account"], -spec["balance"])
            ))
        return {
            "move_type": "entry",
            "journal_id": journal.id,
            "company_id": self.company_id.id,
            "date": self.date,
            "ref": _("Reclassification - %(bill)s", bill=self.name or ""),
            "partner_id": self.partner_id.id,
            "reclass_source_move_id": self.id,
            "line_ids": line_vals,
        }

    def _reclass_generate_mirror_move(self, explain_when_not_applicable=False):
        """Idempotently (re)build the reclassification entry of this bill.

        Any previous mirror is always dropped first, so a bill can never end up
        with more than one active reclassification entry.

        :param explain_when_not_applicable: raise a explicit ``UserError`` instead of
            silently skipping when nothing can be generated (used by the manual button).
        :return: the mirror move, or an empty recordset when not applicable.
        """
        self.ensure_one()
        empty = self.env["account.move"]
        specs = self._reclass_get_mirror_line_specs()
        accounts = self.env["account.account"].union(
            *[spec["account"] for spec in specs]) if specs else None
        journal = self._reclass_get_mirror_journal(accounts=accounts)
        if not specs or not journal:
            # Configuration removed/incomplete: drop any stale mirror and let the
            # native flow stand untouched.
            self._reclass_drop_mirror_moves()
            if specs and not journal:
                _logger.info(
                    "No reclassification journal resolved for bill %s: mirror skipped",
                    self.name)
            if explain_when_not_applicable:
                if not journal:
                    raise UserError(_(
                        "No journal available for the reclassification entry. Set the "
                        "'Reclassification Journal' on the account, on journal "
                        "%(journal)s, or as the company default in the accounting "
                        "settings.",
                        journal=self.journal_id.display_name,
                    ))
                raise UserError(_(
                    "No line of this bill carries a reclassification setup: set the "
                    "'Reclassification Entry' mode with its target and counterpart "
                    "accounts on the accounts used by the lines, and tick 'Generate "
                    "Reclassification Entry' on the journal when required."
                ))
            return empty

        self._reclass_check_lock_dates(self.date, journal)
        self._reclass_drop_mirror_moves()

        mirror = self.env["account.move"].create(
            self._reclass_prepare_mirror_move_vals(journal, specs)
        )
        mirror._post(soft=False)
        self.with_context(skip_is_manually_modified=True).reclass_mirror_move_id = mirror
        _logger.info(
            "reclassification entry %s generated for bill %s", mirror.name, self.name)
        return mirror

    def _reclass_drop_mirror_moves(self):
        """Cancel/remove the reclassification entries of ``self`` and clear the link.

        * never posted -> deleted (no accounting trace to preserve);
        * posted       -> reset to draft and cancelled, keeping the audit trail;
        * cancelled    -> left untouched.
        """
        mirrors = self.env["account.move"].search([
            ("reclass_source_move_id", "in", self.ids),
        ])
        # Safety net: a link that survived while ``reclass_source_move_id`` was lost.
        mirrors |= self.mapped("reclass_mirror_move_id")
        to_delete = self.env["account.move"]
        for mirror in mirrors:
            if mirror.state == "posted":
                mirror._reclass_check_lock_dates(mirror.date, mirror.journal_id)
                mirror.button_draft()
                mirror.button_cancel()
            elif mirror.state == "draft":
                if mirror.posted_before:
                    mirror.button_cancel()
                else:
                    to_delete |= mirror
        self.with_context(skip_is_manually_modified=True).reclass_mirror_move_id = False
        if to_delete:
            to_delete.unlink()

    def _reclass_get_lock_date_violations(self, target_date, journal):
        """Native lock date violations for ``target_date``, or an empty list.

        Wrapped so that a future rename of the native helper degrades into "we do
        not pre-check": the native ``_check_fiscal_lock_dates`` still runs when
        the reclassification entry is created and posted, so a locked period can never be
        written into either way.
        """
        self.ensure_one()
        company = self.company_id
        if not hasattr(company, "_get_lock_date_violations"):
            _logger.info(
                "Reclassification: native lock date API not available, relying on the native "
                "checks performed while posting the reclassification entry")
            return []
        return company._get_lock_date_violations(
            target_date,
            fiscalyear=True,
            sale=journal.type == "sale",
            purchase=journal.type == "purchase",
            tax=False,
            hard=True,
        )

    def _reclass_is_lock_date_free(self):
        """Whether this bill and its current mirror can be written to at all.

        Used by the mass action to skip locked periods instead of aborting the
        whole batch. The single-record path still raises.
        """
        self.ensure_one()
        moves = self | self.reclass_mirror_move_id.filtered(lambda m: m.state == "posted")
        for move in moves:
            if move._reclass_get_lock_date_violations(move.date, move.journal_id):
                return False
        return True

    def _reclass_check_lock_dates(self, target_date, journal):
        """Raise the native ``UserError`` when ``target_date`` sits in a closed period."""
        self.ensure_one()
        violations = self._reclass_get_lock_date_violations(target_date, journal)
        if violations:
            raise UserError(_(
                "The reclassification entry of %(move)s cannot be created or modified: you "
                "cannot add/modify entries prior to and inclusive of: %(lock_date_info)s.",
                move=self.display_name,
                lock_date_info=self.env["res.company"]._format_lock_dates(violations),
            ))
        return True
