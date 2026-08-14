import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import config

# Placeholder Odoo emits for a LATAM document number when the document-type
# prefix is missing (e.g. ``'False 00001001'``).  A serie parsed out of such a
# string ('False') is garbage and must never reach the PLE (see design doc
# 3.2, the "'False '" rule).
_FALSE_PREFIX = 'False'

# account.move types we ever populate from.  Everything else (entries,
# receipts without an invoice, etc.) is out of scope -> field stays empty ->
# the bridge inherits the native report behaviour.
_INVOICE_TYPES = ('out_invoice', 'in_invoice', 'out_refund', 'in_refund')
_REFUND_TYPES = ('out_refund', 'in_refund')

# Mass/historic operations run per-move (O(N) writes), so on very large
# databases (~1M moves) they must be chunked with commits between batches
# instead of one giant transaction (design doc 3.4).
_ITDE_BATCH_SIZE = 1000


class StockMove(models.Model):
    """PLE 13.1 capture, at the *movement* level.

    Multi-document-per-picking is extremely common (purchases and sales), so
    the supporting document (type + serie + number) is captured per stock.move,
    not per picking.  The bridge module reads these fields; nobody else does.
    """

    _inherit = 'stock.move'

    # copy=False on the three capture fields: a copied move (a wizard-created
    # RETURN is a copy of the original, and so is a duplicated picking) backs a
    # DIFFERENT document — it must start empty and derive its own (the return
    # wizard leak: without this the return clones the original invoice).
    transfer_document_type_id = fields.Many2one(
        comodel_name='l10n_latam.document.type',
        string='Doc Type',
        domain="[('country_id.code', '=', 'PE')]",
        copy=False,
        help="Document type backing this movement for the PLE 13.1 (Kardex). "
             "If left blank, the Kardex falls back to the native behaviour "
             "(remission guide, invoice name, default 00).",
    )
    serie_transfer_document = fields.Char(
        string='Serie',
        copy=False,
        help="Document series backing this movement for the PLE 13.1 (Kardex).",
    )
    number_transfer_document = fields.Char(
        string='Correlativo',
        copy=False,
        help="Document number backing this movement for the PLE 13.1 (Kardex).",
    )
    manual_override = fields.Boolean(
        string='Transfer Doc Manually Set',
        default=False,
        copy=False,
        help="Set automatically when a user edits the transfer document fields "
             "by hand.  Automatic population never overwrites a move flagged "
             "this way.",
    )

    # ------------------------------------------------------------------
    # manual_override mechanism (design doc 3.1)
    # ------------------------------------------------------------------
    def write(self, vals):
        """Flag manual edits so automatic population never clobbers them.

        Any write that touches the three transfer fields *without* the
        ``auto_populate=True`` context flag is a human edit -> mark
        ``manual_override``.  Every programmatic writer (events, mass action,
        quick-set, migration) passes ``auto_populate=True`` and therefore never
        trips this.
        """
        transfer_keys = {
            'transfer_document_type_id',
            'serie_transfer_document',
            'number_transfer_document',
        }
        if (
            transfer_keys & set(vals)
            and not self.env.context.get('auto_populate')
            and 'manual_override' not in vals
        ):
            vals = dict(vals, manual_override=True)
        return super().write(vals)

    # ------------------------------------------------------------------
    # SUNAT format constraint (design doc 3.1) - model level so it applies to
    # manual edits AND the bridge injection, not only to auto-population.
    # ------------------------------------------------------------------
    @api.constrains('serie_transfer_document', 'number_transfer_document')
    def _check_transfer_document_format(self):
        for move in self:
            if move.serie_transfer_document and len(move.serie_transfer_document) > 20:
                raise ValidationError(_(
                    "The transfer document series must be 20 characters or fewer "
                    "(got %s).", move.serie_transfer_document,
                ))
            if move.number_transfer_document and len(move.number_transfer_document) > 20:
                raise ValidationError(_(
                    "The transfer document number must be 20 characters or fewer "
                    "(got %s).", move.number_transfer_document,
                ))
            number = (move.number_transfer_document or '').strip()
            if number and number.lstrip('-').isdigit() and int(number) < 0:
                raise ValidationError(_(
                    "The transfer document number must be positive (got %s).",
                    number,
                ))

    # ------------------------------------------------------------------
    # serie/folio parser - same digit-run logic as the native wizard (no
    # dependency on l10n_pe_reports_stock, design doc 3.2 decision A1), but
    # DELIBERATELY not identical since v19.0.2.5.0: spaces are stripped from
    # the serie, mirroring how the PE EDI normalizes the CPE serie
    # ('F 101-...' -> 'F101').  The native report keeps the space and thus
    # never matches the serie actually declared to the tax authority.
    # ------------------------------------------------------------------
    @api.model
    def _itde_get_serie_folio(self, number):
        values = {"serie": "", "folio": ""}
        number_matchs = list(re.finditer(r"\d+", number or ""))
        if number_matchs:
            last_number_match = number_matchs[-1]
            values["serie"] = (
                number[: last_number_match.start()]
                .replace("-", "").replace(" ", "") or ""
            )
            values["folio"] = last_number_match.group() or ""
        return values

    # ------------------------------------------------------------------
    # Which invoice backs this move (design doc 3.2)
    # ------------------------------------------------------------------
    def _itde_source_invoice(self):
        """Return the posted invoice/bill/refund backing *this* move, or empty.

        Uses only native stock/account signals (never l10n_pe_operation_type):
        the invoice of the move's own line, ``sorted('id')[:1]`` so the
        first-created document wins and the advance/down-payment (whose line is
        not the product line) is excluded.  Returns whatever is found (empty
        recordset if none).
        """
        self.ensure_one()
        Move = self.env['account.move']
        # Return move FIRST: the return wizard creates the return move as a
        # copy of the original, so it also carries sale_line_id /
        # purchase_line_id (that is how Odoo decreases the delivered/received
        # qty on the order).  If the order-line branches ran first, every
        # wizard-created return would inherit the original INVOICE instead of
        # its credit note.  Navigate to the original line via
        # origin_returned_move_id, then to its CREDIT NOTES only (design doc
        # 3.2, decision C3): a return never resolves to the original invoice —
        # with no posted credit note it stays empty (guide / native fallback).
        origin = self.origin_returned_move_id
        if origin:
            if origin.sale_line_id:
                refunds = origin.sale_line_id.invoice_lines.move_id.filtered(
                    lambda m: m.move_type == 'out_refund' and m.state == 'posted'
                )
                return refunds.sorted('id')[:1]
            if origin.purchase_line_id:
                refunds = origin.purchase_line_id.invoice_lines.move_id.filtered(
                    lambda m: m.move_type == 'in_refund' and m.state == 'posted'
                )
                return refunds.sorted('id')[:1]
            return Move
        # Direct delivery / receipt: the invoice of the move's own order line.
        if self.sale_line_id:
            candidates = self.sale_line_id.invoice_lines.move_id.filtered(
                lambda m: m.move_type == 'out_invoice' and m.state == 'posted'
            )
            return candidates.sorted('id')[:1]
        if self.purchase_line_id:
            candidates = self.purchase_line_id.invoice_lines.move_id.filtered(
                lambda m: m.move_type == 'in_invoice' and m.state == 'posted'
            )
            return candidates.sorted('id')[:1]
        return Move

    def _itde_document_values(self):
        """Return ``(doc_type, serie, number)`` for this move, or ``None``.

        Priority (deliberately the reverse of the native report): OUR invoice
        derivation first, and only if there is no sale/purchase invoice, the
        remission guide on the picking.  The *type* is always set (the anchor)
        so serie/number never travel alone.
        """
        self.ensure_one()
        return self._itde_invoice_values() or self._itde_guide_values()

    def _itde_invoice_values(self):
        """``(doc_type, serie, number)`` from the move's own invoice, or None.

        The source string depends on the document's SIDE (v19.0.2.5.0):

        * OWN documents (out_invoice/out_refund): the ``name`` (doc-type
          prefix included).  The fiscal serie of an emitted document is what
          the EDI declares, and the (PE) EDI builds it by parsing the name
          with spaces stripped -- so 'F 101-...' yields 'F101' even when the
          journal seed keeps the letter out of the number ('101-...'), where
          the canonical ``l10n_latam_document_number`` would lose it.
        * RECEIVED documents (in_invoice/in_refund): the canonical
          ``l10n_latam_document_number`` (-> ref -> name).  The user types
          the supplier's real number there; the name PREPENDS our own doc
          prefix on top of it ('F F 101-...'), so parsing the name would
          fabricate a doubled serie.
        """
        invoice = self._itde_source_invoice()
        if not invoice:
            return None
        doc_type = invoice.l10n_latam_document_type_id
        if not doc_type:
            return None
        if invoice.move_type in ('out_invoice', 'out_refund'):
            number_str = invoice.name or ''
        else:
            # Priority: l10n_latam_document_number -> ref -> name (name is
            # last resort: it may be the bad internal sequence -> R2
            # limitation).
            number_str = (
                invoice.l10n_latam_document_number
                or invoice.ref
                or invoice.name
                or ''
            )
        # "'False '" rule: a name like 'False 00001001' would parse to serie
        # 'False' -> garbage.  Better empty (fall back to native) than a bad
        # serie (design doc 3.2).
        if number_str.strip().startswith(_FALSE_PREFIX):
            return None
        parsed = self._itde_get_serie_folio(number_str)
        serie, number = parsed['serie'], parsed['folio']
        if not serie and not number:
            return None
        return (doc_type, serie, number)

    def _itde_guide_values(self):
        """``(doc_type, serie, number)`` from the picking's remission guide, or
        None.  Used only when there is no sale/purchase invoice, so the field is
        visibly filled instead of relying silently on the native fallback.

        A remission guide is ALWAYS SUNAT document type '09' (Guia de Remision
        Remitente); we resolve that type by code and NEVER read the picking's
        reason-for-transfer (``l10n_pe_edi_reason_for_transfer``), keeping the
        capture decoupled from the operation/transfer-reason.
        """
        guide_number = self._itde_guide_number()
        if not guide_number or guide_number.strip().startswith(_FALSE_PREFIX):
            return None
        parsed = self._itde_get_serie_folio(guide_number)
        serie, number = parsed['serie'], parsed['folio']
        if not serie and not number:
            return None
        guide_type = self._itde_guide_document_type()
        if not guide_type:
            return None
        return (guide_type, serie, number)

    def _itde_guide_number(self):
        """The remission guide number on the picking, or '' if the field is
        absent (l10n_pe_edi_stock not installed)."""
        picking = self.picking_id
        if 'l10n_latam_document_number' not in picking._fields:
            return ''
        return picking.l10n_latam_document_number or ''

    def _itde_guide_document_type(self):
        """The SUNAT '09' document type (Guia de Remision Remitente), resolved
        by code for the move's company.  Never derived from the picking's
        reason-for-transfer (keeps the capture decoupled from the operation)."""
        return self.env['l10n_latam.document.type'].search([
            ('code', '=', '09'),
            ('country_id', '=', self.company_id.country_id.id),
        ], limit=1)

    # ------------------------------------------------------------------
    # Population (design doc 3.2 / 3.3)
    # ------------------------------------------------------------------
    def _itde_populate_documents(self, force=False, force_manual=False):
        """Fill the transfer fields from each move's backing document.

        * ``force=False`` (events): only moves whose fields are empty.
        * ``force=True`` (mass "force"): also overwrite NON-manual moves.
        * ``force_manual=True``: also overwrite manual moves (explicit confirm).

        Always writes with ``auto_populate=True`` so it never sets
        ``manual_override``.  Never erases a good value with an empty recompute
        (anti-empty guard, design doc 3.4).
        """
        latam_cache = {}

        def is_latam(company):
            if company.id not in latam_cache:
                latam_cache[company.id] = bool(company.country_id) and bool(
                    self.env['l10n_latam.document.type'].search_count(
                        [('country_id', '=', company.country_id.id)], limit=1
                    )
                )
            return latam_cache[company.id]

        for move in self:
            # Early-exit: LATAM scope, per-move company (never self.env.company).
            company = move.company_id
            if not is_latam(company):
                continue
            # Respect manual edits.
            if move.manual_override and not force_manual:
                continue
            already_filled = bool(move.transfer_document_type_id)
            if already_filled and not (force or force_manual):
                continue
            values = move._itde_document_values()
            if not values:
                # Anti-empty guard: don't wipe a good value on empty recompute.
                continue
            doc_type, serie, number = values
            move.with_context(auto_populate=True).write({
                'transfer_document_type_id': doc_type.id,
                'serie_transfer_document': serie,
                'number_transfer_document': number,
            })

    def _itde_clear_auto(self):
        """Clear the transfer fields on NON-manual moves (invoice unposted)."""
        clearable = self.filtered(
            lambda m: not m.manual_override and m.transfer_document_type_id
        )
        if clearable:
            clearable.with_context(auto_populate=True).write({
                'transfer_document_type_id': False,
                'serie_transfer_document': False,
                'number_transfer_document': False,
            })

    # ------------------------------------------------------------------
    # stock.move event: moves really became done (design doc 3.3).
    # _action_done (NOT button_validate) is the reliable seam and also covers
    # backorder moves.
    # ------------------------------------------------------------------
    def _action_done(self, cancel_backorder=False):
        moves = super()._action_done(cancel_backorder=cancel_backorder)
        if moves:
            moves._itde_populate_documents()
        return moves

    # ------------------------------------------------------------------
    # Mass actions (historic R2 - design doc 3.4)
    # ------------------------------------------------------------------
    def _itde_mass_populate(self, force=False, force_manual=False):
        """Batched populate for mass/historic use: process in chunks and commit
        between them, so it scales to very large selections without one giant
        transaction (design doc 3.4).  Small selections (a single chunk) are not
        committed, keeping event-driven and test flows transactional."""
        total = len(self)
        multi_chunk = total > _ITDE_BATCH_SIZE
        for offset in range(0, total, _ITDE_BATCH_SIZE):
            chunk = self[offset:offset + _ITDE_BATCH_SIZE]
            chunk._itde_populate_documents(force=force, force_manual=force_manual)
            if multi_chunk:
                if not config['test_enable']:
                    self.env.cr.commit()  # batch checkpoint (forbidden under tests)
                self.env.invalidate_all()

    def action_itde_fill_empty(self):
        """Fill only empty moves (default mass mode)."""
        self._itde_mass_populate(force=False)

    def action_itde_force(self):
        """Re-derive and overwrite NON-manual moves (manuals are preserved)."""
        self._itde_mass_populate(force=True)

    def action_itde_force_including_manual(self):
        """Overwrite even manual moves - only from an explicit confirmation."""
        self._itde_mass_populate(force=True, force_manual=True)

    # ------------------------------------------------------------------
    # Recover the legacy value that older versions stored on the picking.
    # Same effect as the upgrade migration, but on the current selection and on
    # demand.  (To be deprecated in Odoo 21 together with the picking fields.)
    # ------------------------------------------------------------------
    @api.model
    def _itde_copy_legacy_sql(self, extra_where, params, skip_manual=False):
        """Copy the legacy picking transfer document onto stock.move via raw SQL
        (bypasses the SUNAT format constraint for long historical values),
        FK-guarding the document type.  ``extra_where`` is a trusted, hardcoded
        SQL predicate on ``sm`` (with %s placeholders) and ``params`` its values,
        applied to BOTH statements.

        ``skip_manual=True`` protects hand-edited moves: the raw SQL otherwise
        overwrites any current value (it does not go through the ORM's
        manual_override guard), so callers that want to honour manual edits pass
        this to append ``AND sm.manual_override IS NOT TRUE``.  Default is False
        to preserve the historic recover-everything behaviour (migration, range
        wizard).  Returns (serie/number rows, type rows)."""
        if 'transfer_document_type_id' not in self.env['stock.picking']._fields:
            return (0, 0)
        if skip_manual:
            # Trusted, constant predicate (no placeholder): keep manual moves.
            extra_where = f"{extra_where} AND sm.manual_override IS NOT TRUE"
        self.env.flush_all()  # push pending ORM writes before the raw SQL
        cr = self.env.cr
        cr.execute(f"""
            UPDATE stock_move sm
               SET serie_transfer_document = sp.serie_transfer_document,
                   number_transfer_document = sp.number_transfer_document,
                   manual_override = TRUE
              FROM stock_picking sp
             WHERE sm.picking_id = sp.id
               AND (sp.serie_transfer_document IS NOT NULL
                    OR sp.number_transfer_document IS NOT NULL)
               {extra_where}
        """, params)
        values_rows = cr.rowcount
        cr.execute(f"""
            UPDATE stock_move sm
               SET transfer_document_type_id = sp.transfer_document_type_id,
                   manual_override = TRUE
              FROM stock_picking sp
             WHERE sm.picking_id = sp.id
               AND sp.transfer_document_type_id IS NOT NULL
               AND EXISTS (
                   SELECT 1 FROM l10n_latam_document_type t
                    WHERE t.id = sp.transfer_document_type_id
               )
               {extra_where}
        """, params)
        return (values_rows, cr.rowcount)

    def action_itde_recover_legacy(self, skip_manual=False):
        """Recover onto the SELECTED moves the serie/number/type that older
        versions stored on their picking (still kept in the hidden legacy picking
        fields), flagging manual_override.  Batched with commits for large
        selections.

        ``skip_manual=True`` leaves hand-edited moves untouched (see
        _itde_copy_legacy_sql); default False keeps the historic behaviour."""
        ids = self.ids
        multi = len(ids) > _ITDE_BATCH_SIZE
        for offset in range(0, len(ids), _ITDE_BATCH_SIZE):
            chunk = ids[offset:offset + _ITDE_BATCH_SIZE]
            self._itde_copy_legacy_sql(
                "AND sm.id = ANY(%s)", [chunk], skip_manual=skip_manual)
            if multi and not config['test_enable']:
                self.env.cr.commit()  # batch checkpoint (forbidden under tests)
        self.invalidate_recordset()

    @api.model
    def _itde_scan_suspects(self, domain=None, limit=None):
        """Return moves whose stored serie/number differs from the document we
        would derive now.  A method, not a search domain: detecting "stored
        value != expected value" requires re-deriving the document per move.

        Scanned in id-ordered batches with cache invalidation between them, so a
        multi-million-row table does not have to be loaded at once.
        """
        base_domain = [
            ('state', '=', 'done'),
            ('product_id.is_storable', '=', True),
        ]
        if domain:
            base_domain += domain
        Move = self.env['stock.move']
        suspect_ids = []
        offset = 0
        while True:
            batch = Move.search(
                base_domain, offset=offset, limit=_ITDE_BATCH_SIZE, order='id')
            if not batch:
                break
            suspect_ids += self._itde_suspect_ids(batch)
            if limit and len(suspect_ids) >= limit:
                suspect_ids = suspect_ids[:limit]
                break
            offset += _ITDE_BATCH_SIZE
            self.env.invalidate_all()  # free the browsed batch from the cache
        return Move.browse(suspect_ids)

    @api.model
    def _itde_suspect_ids(self, moves):
        ids = []
        for move in moves:
            if move.manual_override:
                continue
            values = move._itde_document_values()
            if not values:
                continue
            _doc_type, serie, number = values
            if (
                serie != (move.serie_transfer_document or '')
                or number != (move.number_transfer_document or '')
            ):
                ids.append(move.id)
        return ids
