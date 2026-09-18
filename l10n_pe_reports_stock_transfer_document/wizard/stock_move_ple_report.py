import csv
from datetime import timedelta
from io import StringIO

from odoo import api, fields, models
from odoo.tools import float_repr


class L10n_PeStockPleWizard(models.TransientModel):
    _inherit = 'l10n_pe.stock.ple.wizard'

    # ------------------------------------------------------------------
    # Late revaluations: the period as it was known (design v4, D7)
    # ------------------------------------------------------------------
    # stock_landed_cost_variance 19.0.2 writes a late revaluation into the stored
    # value of the movements, with a dated record of every amount.  Printed
    # natively, a period already filed would change when regenerated: a freight
    # of September lands in the August file, and the August closing no longer
    # matches the September opening.  With the engine installed the 13.1 prints
    # every movement as it was known at the end of the period, and each later
    # amount in the period of its event, with the event date.  Measured on the
    # real TXT: filed periods regenerate byte-identical, opening == previous
    # closing, closing == PLE 3.7 == stock valuation account.
    #
    # Soft guard: without the engine every helper is inert and the report is the
    # native one.
    def _l10n_pe_known_at_enabled(self):
        return 'stock.value.variance' in self.env and hasattr(
            self.env['product.product'], '_variance_value_known_at')

    def _l10n_pe_period_end(self):
        return fields.Datetime.to_datetime(self.date_to).replace(hour=23, minute=59, second=59)

    def _l10n_pe_move_variances(self, move):
        """Amounts no stored value carries (value dropped by the engine), known at the period end."""
        if not self._l10n_pe_known_at_enabled():
            return self.env['stock.move'].browse()
        return self.env['stock.value.variance'].sudo().search([
            ('move_id', '=', move.id),
            ('absorbed', '=', False),
            ('kind', '!=', 'legacy'),
            ('date', '<=', self._l10n_pe_period_end()),
        ], order='date, id')

    def _l10n_pe_folded_later(self, move):
        """Amounts folded into the stored value by events dated after the period."""
        if not self._l10n_pe_known_at_enabled():
            return 0.0
        rows = self.env['stock.value.variance'].sudo().search([
            ('move_id', '=', move.id),
            ('absorbed', '=', True),
            ('kind', '!=', 'legacy'),
            ('date', '>', self._l10n_pe_period_end()),
        ])
        return sum(rows.mapped('ledger_amount'))

    def _l10n_pe_adjustment_in_period(self, adjustment):
        """A landed cost dated after the period did not exist when the period was filed."""
        day, month, year = adjustment['date'].split('/')
        return fields.Date.to_date(f'{year}-{month}-{day}') <= self.date_to

    def _l10n_pe_variance_adjustment_vals(self, variance):
        """Shape a live amount as an adjustment line for ``_build_adjustment_line``.

        Its own CUO namespace: the base uses the move id, the landed-cost bridge
        ``{id}LC`` and the openings ``{id}A1``, so a fourth is needed or two
        lines of the same file would share a CUO.

        Operation type 99 ("Otros"). The catalogue has no code for a value
        adjustment -- 26/27 are production-service entry/exit and 28 is an
        inventory *quantity* difference.
        """
        serie_folio = self._get_serie_folio(
            variance.revaluation_id.name or variance.move_id.reference or '')
        return {
            'cuo': f'{variance.id}VA'.zfill(6),
            'value': variance.ledger_amount,
            'operation_type': '99',
            'date': variance.date.strftime('%d/%m/%Y'),
            'document_type': '00',
            'serie': serie_folio['serie'].replace(' ', '').replace('/', '') or '0',
            'folio': serie_folio['folio'].replace(' ', '') or '0',
        }

    def _l10n_pe_event_adjustment_vals(self, event):
        """A late amount of this period on a movement of an earlier one, dated on its event.

        Landed costs keep the native CUO and operation type 26; amounts recorded by
        the engine (restated exits, bills, value dropped) use ``{id}EV`` and 99.
        """
        serie_folio = self._get_serie_folio(event['reference'] or '')
        landed = event['kind'] == 'landed_cost'
        return {
            'cuo': event['cuo'].zfill(6),
            'value': event['value'],
            'operation_type': '26' if landed else '99',
            'date': event['date'].strftime('%d/%m/%Y'),
            'document_type': '00',
            'serie': serie_folio['serie'].replace(' ', '').replace('/', '') or '0',
            'folio': serie_folio['folio'].replace(' ', '') or '0',
        }

    def _l10n_pe_events_in_period(self):
        """{product: [(move, event)]} for late amounts dated in the period on earlier movements."""
        if not self._l10n_pe_known_at_enabled():
            return {}
        company = self.env.company
        start = fields.Datetime.to_datetime(self.date_from)
        products = self.env['stock.valuation.adjustment.lines'].sudo().search([
            ('cost_id.state', '=', 'done'), ('cost_id.company_id', '=', company.id),
            ('cost_id.date', '>=', self.date_from), ('cost_id.date', '<=', self.date_to),
            ('move_id.date', '<', start),
        ]).product_id | self.env['stock.value.variance'].sudo().search([
            ('company_id', '=', company.id), ('kind', '!=', 'legacy'),
            ('date', '>=', start), ('date', '<=', self._l10n_pe_period_end()),
            ('move_id.date', '<', start),
        ]).product_id
        result = {}
        for product in products.filtered('is_storable').sorted('id'):
            events = product.with_company(company)._variance_events_in_period(self.date_from, self.date_to)
            if events:
                result[product] = events
        return result

        # ------------------------------------------------------------------
    # Existence code and catalogues (SUNAT fields 5, 7 and 8)
    # ------------------------------------------------------------------
    @api.model
    def _product_row_values(self, product):
        """Fields 5, 7 and 8 as the norm defines them.

        The native method hardcodes a '1' (United Nations) in field 5 while
        field 7 carries the internal reference, and a '1' in field 8 even when
        field 9 goes empty.  Per RS 108-2020, field 5 declares the catalogue *of
        the code in field 7* -- so it is configured on the product -- and field
        8 declares the catalogue of field 9, which is only emitted when there is
        a code there.  An empty field 8 is the column with no content: the field
        is optional and does not accept the value 9.
        """
        values = super()._product_row_values(product)
        # Supersedes the context-gated cleanup of v19.0.3.0.1: the scrub now
        # lives in ``_l10n_pe_ple_existence_code`` (same rule, task 69361) and
        # applies to every source, so the report, the audit and the product
        # preview can never disagree about what the TXT will carry.
        template = product.product_tmpl_id
        values['default_code'] = product._l10n_pe_ple_existence_code()
        values['catalogue'] = template.l10n_pe_existence_catalogue or '9'
        values['catalogue_used'] = '1' if values['unspsc'] else ''
        return values

    def _l10n_pe_document_date(self, move, invoice, bill):
        """Field 10: the issue date OF THE DOCUMENT THIS ROW REPORTS.

        Two defects of the native cascade, both measured on a live ledger
        (Importaciones Huarcaya, 2026: 236.107 movements carrying a captured
        document).

        1. MIXED PROVENANCE -- 14.005 rows.  Fields 11/12/13 are injected from
           the captured document further down, while this date stayed native:
           ``sorted('id')[:1]`` with no type filter.  On a return whose order
           line carries both the invoice and its credit note, the first by id
           is the INVOICE, so the row printed the credit note's number with the
           invoice's date.  13.995 of the 14.005 are exactly that.  The date
           and the number did not belong to each other -- which the norm does
           not reject (field 10 is only bounded above) but which no reader can
           reconcile.

        2. DRAFT DATES -- 163 rows take field 10 from an UNPOSTED document.
           Field 10 is the document's *issue* date and a draft has not been
           issued, so drafts are dropped from the fallback.

        The first correction is GATED on the captured type matching what the
        capture module derives right now.  Where the stored document is a
        legacy leftover that disagrees with the derivation -- the sealed
        movements still pending reprocessing -- taking its date would only
        spread a document already known to be the wrong one.  Those keep the
        native date until they are reprocessed, and then fall in line on their
        own.  Measured: of the 14.005, only the 1.737 real returns pass this
        gate; the 12.268 whose stored credit note is itself the legacy error do
        not, which is precisely the intent.

        ``invoice`` and ``bill`` arrive already resolved by the caller and are
        NOT recomputed here: they also feed serie/folio and the native document
        type, and this fix must not move those.
        """
        source = None
        if move.transfer_document_type_id and hasattr(move, '_itde_source_invoice'):
            candidate = move._itde_source_invoice()
            if (candidate.l10n_latam_document_type_id
                    == move.transfer_document_type_id):
                source = candidate
        if source and source.invoice_date:
            return source.invoice_date
        posted = (invoice | bill).filtered(lambda m: m.state == 'posted')
        return posted.sorted('id')[:1].invoice_date or move.date

    def _l10n_pe_apply_opening_existence_type(self, rows):
        """Field 6 of the opening rows, from the product like the movement rows.

        Both native builders force '99' regardless of the product, so the same
        existence prints 01 in its movements and 99 in its opening inside a
        single file.  The product is recovered from the CUO, which the native
        code builds deterministically as ``f'{product.id}A1'.zfill(6)``; a row
        whose CUO does not parse is left untouched rather than guessed at.
        Applies to 12.1 and 13.1 alike: field 6 exists in both.
        """
        for row in rows:
            cuo = (row.get('cuo') or '').lstrip('0')
            if not cuo.endswith('A1'):
                continue
            try:
                product_id = int(cuo[:-2])
            except ValueError:
                continue
            product = self.env['product.product'].browse(product_id).exists()
            if not product:
                continue
            row['type_of_existence'] = (
                product.product_tmpl_id.l10n_pe_type_of_existence or '99').zfill(2)
        return rows

    # ------------------------------------------------------------------
    # Opening balances
    # ------------------------------------------------------------------
    def _l10n_pe_apply_opening_known_at(self, rows, report):
        """Opening value = value known at the end of the day before the period.

        Both opening builders live in the native module and sum the stored values,
        which already carry every later revaluation.  The known value takes those
        out again, so the opening is exactly the closing of the previous period as
        it was filed.

        The product is recovered from the CUO, which the native code builds
        deterministically as ``f'{product.id}A1'.zfill(6)`` in both builders.  A
        row whose CUO does not parse is left untouched rather than guessed at.
        """
        if report == '1201' or not rows or not self._l10n_pe_known_at_enabled():
            # 12.1 carries physical units only.
            return rows
        day_before = self.date_from - timedelta(days=1)
        for row in rows:
            cuo = (row.get('cuo') or '').lstrip('0')
            if not cuo.endswith('A1'):
                continue
            try:
                product_id = int(cuo[:-2])
            except ValueError:
                continue
            product = self.env['product.product'].browse(product_id).exists()
            if not product:
                continue
            quantity = row.get('remaining', 0)
            value = product.with_company(self.env.company)._variance_value_known_at(day_before)[1]
            row.update(self._valuation_columns(
                quantity, value, quantity, value, is_balance=True))
        return rows

    def _append_valuation_line(self, move, period, report):
        values = super()._append_valuation_line(move, period, report)
        if not values:
            return values
        rows = self._l10n_pe_apply_opening_existence_type([values])
        return self._l10n_pe_apply_opening_known_at(rows, report)[0]

    def _append_historic_valuation_lines(self, products, period, report):
        rows = super()._append_historic_valuation_lines(products, period, report)
        rows = self._l10n_pe_apply_opening_existence_type(rows)
        return self._l10n_pe_apply_opening_known_at(rows, report)

    def _get_ple_report_content(self, report):
        """Copy of the native ``_get_ple_report_content`` with a single, atomic
        injection: when a move carries a captured transfer document *type*, its
        type/serie/number replace the natively-derived ones.

        The injection happens AFTER the native force-to-'09' and BEFORE the
        scrub, and is gated on ``transfer_document_type_id`` (the anchor) so it
        can never turn a compliant '09'/invoice line into an illegal '00'.

        The rest of the method is a verbatim copy of the native one; the
        regression test (fingerprint + native-vs-bridge comparison) fails the
        build if the native source drifts and this copy must be re-synced.
        """
        data = []
        period = '%s%s00' % (self.date_from.year, str(self.date_from.month).zfill(2))
        moves = self._get_ple_reports_data()
        data_per_products = {}
        delivery_number_installed = 'l10n_latam_document_number' in self.env['stock.picking']._fields

        adjustments_by_move = self._get_move_valuation_adjustments(moves)
        for move in moves:
            product = move.product_id
            product_tmpl = product.product_tmpl_id
            # Sort by id to consistently pick the first-created invoice,
            # matching 18.0's SQL behavior (ORDER BY am.id / am_p.id NULLS LAST).
            # account.move default _order is 'date desc, id desc' so [:1] alone
            # would incorrectly pick the latest invoice.
            invoice = move.sale_line_id.invoice_lines.move_id.sorted('id')[:1]
            bill = move.purchase_line_id.invoice_lines.move_id.sorted('id')[:1]

            picking_name = move.picking_id.name or ''
            delivery_number = (
                move.picking_id.l10n_latam_document_number
                if delivery_number_installed and move.picking_id.l10n_latam_document_number
                else ''
            )
            serie_folio = self._get_serie_folio(
                delivery_number or invoice.name or bill.name or picking_name or ''
            )
            date = self._l10n_pe_document_date(move, invoice, bill)

            # === BRIDGE FIX: field 10 <= the period of field 1 (RS 108-2020) ===
            # The norm validates the document date against the period, and the
            # native cascade prefers the invoice date: a delivery of 30/05
            # invoiced on 02/06 prints 02/06 in the May file and SUNAT rejects
            # it.  The comparison is by period (year, month) as the norm states,
            # not against date_to; dates *earlier* than the period are allowed
            # and left alone.
            if date and (date.year, date.month) > (
                    self.date_from.year, self.date_from.month):
                date = move.date
            # === END FIELD 10 FIX ===

            date = date.strftime('%d/%m/%Y') if date else ''

            document_type_code = (
                (invoice.l10n_latam_document_type_id or bill.l10n_latam_document_type_id).code or '00'
            )
            operation_type = (move.picking_id.l10n_pe_operation_type or '99').zfill(2)
            if not move.picking_id.l10n_pe_operation_type and move.picking_type_id.code == 'mrp_operation':
                operation_type = '19' if move.is_in else '27'

            # === BRIDGE INJECTION: move-level SUNAT operation type ===
            # If the move carries a per-move operation type (captured by
            # l10n_pe_stock_operation_type), it wins over the picking-derived
            # value.  Placed BEFORE the '01..06 + doc 00 -> 09' coupling below,
            # and before the mrp fallback effectively, so that coupling reads the
            # overridden value.  Soft-guarded on the field's presence -> fully
            # inert when that capture module is not installed (the native
            # picking-derived operation_type stands, "si no hay, lo nativo").
            if ('l10n_pe_operation_type' in move._fields
                    and move.l10n_pe_operation_type):
                operation_type = move.l10n_pe_operation_type.zfill(2)
            # === END OPERATION-TYPE INJECTION ===

            if delivery_number or (
                operation_type in ('01', '02', '03', '04', '05', '06') and document_type_code == '00'
            ):
                document_type_code = '09'

            # === BRIDGE INJECTION (after the '09' forcing, before the scrub) ===
            # Gate on the captured *type*: if present, the captured document wins
            # atomically (type + serie + folio from the same move); serie/folio
            # are taken directly (already split) and inherit the native scrub.
            # No type -> no injection -> the native result (09/guide/00) stands.
            if move.transfer_document_type_id:
                document_type_code = move.transfer_document_type_id.code
                serie_folio = {
                    'serie': move.serie_transfer_document or '',
                    'folio': move.number_transfer_document or '',
                }
            # === END BRIDGE INJECTION ===

            # Opening balance line for first occurrence of each product
            if product.id not in data_per_products:
                valuation_data = self._append_valuation_line(move, period, report)
                data_per_products[product.id] = [
                    valuation_data.get('remaining', 0),
                    valuation_data.get('value', 0),
                ]
                if valuation_data:
                    data.append(valuation_data)

            # Compute quantity and value for this move
            quantity = move._get_valued_qty() if move.is_in else -move._get_valued_qty()
            if report == '1201' and not quantity:
                continue
            if not quantity:
                operation_type = '99'

            values = {
                'period': period,
                'cuo': str(move.id).zfill(6),
                'number': 'M1',
                'establishment': move.warehouse_id.l10n_pe_anexo_establishment_code or '0000',
                **self._product_row_values(product),
                'date': date,
                'document_type': document_type_code,
                'serie': serie_folio['serie'].replace(' ', '').replace('/', '') or '0',
                'folio': serie_folio['folio'].replace(' ', '') or '0',
                'operation_type': operation_type,
                'product': self._product_name(product),
                'uom': move.product_uom.l10n_pe_edi_measure_unit_code,
            }
            if report == '1201':
                values.update({
                    'qty_in': quantity if quantity > 0 else 0,
                    'qty_out': quantity if quantity <= 0 else 0,
                    'state': '1',
                })
                data.append(values)
                continue

            adjustments = adjustments_by_move.get(move.id, [])
            total_cost = (move.value if move.is_in else -abs(move.value)) - sum(a['value'] for a in adjustments)
            # INJECTION 3 (soft-guarded): the movement as known at the period end.
            # (a) amounts folded into the stored value by later events come out;
            # (b) landed costs dated after the period are not printed -- they print
            #     in their own period, below;
            # a live amount (value dropped by the engine) on an OUTGOING move is
            # part of the exit cost and goes into the line; on an INCOMING one it
            # must not, or the line would print a unit cost the goods never had.
            if self._l10n_pe_known_at_enabled():
                total_cost -= self._l10n_pe_folded_later(move)
                adjustments = [a for a in adjustments if self._l10n_pe_adjustment_in_period(a)]
            variances = self._l10n_pe_move_variances(move)
            if variances and move.is_out:
                total_cost += sum(v.ledger_amount for v in variances)
                variances = variances.browse()
            balance = data_per_products[product.id]
            balance[0] += quantity
            balance[1] += total_cost
            values.update({
                'valuation': self._get_stock_valuation(product_tmpl.categ_id.id),
                **self._valuation_columns(quantity, total_cost, balance[0], balance[1]),
                'state': '1',
            })
            data.append(values)

            # Each valuation adjustment (e.g. a landed cost) gets its own line.
            for adjustment in adjustments:
                balance[1] += adjustment['value']
                data.append(self._build_adjustment_line(move, product, period, adjustment, balance))

            # INJECTION 3 continued: a live amount on an entry gets its own line.
            for variance in variances:
                balance[1] += variance.ledger_amount
                data.append(self._build_adjustment_line(
                    move, product, period,
                    self._l10n_pe_variance_adjustment_vals(variance), balance))

        # INJECTION 3, (c): late amounts of this period on movements of earlier
        # periods, printed here with the date of their event.
        if report != '1201':
            for product, events in self._l10n_pe_events_in_period().items():
                if product.id not in data_per_products:
                    valuation_data = self._append_valuation_line(events[0][0], period, report)
                    data_per_products[product.id] = [
                        valuation_data.get('remaining', 0),
                        valuation_data.get('value', 0),
                    ]
                    if valuation_data:
                        data.append(valuation_data)
                balance = data_per_products[product.id]
                for event_move, event in events:
                    adjustment = self._l10n_pe_event_adjustment_vals(event)
                    balance[1] += adjustment['value']
                    data.append(self._build_adjustment_line(event_move, product, period, adjustment, balance))
        data.extend(self._append_historic_valuation_lines(list(data_per_products), period, report))
        if not data:
            return ''

        float_fields = (
            "qty_in", "cost_in", "value_in",
            "qty_out", "cost_out", "value_out",
            "remaining", "unit_cost_final", "value",
        )
        for element in data:
            for field in float_fields:
                if field in element:
                    element[field] = float_repr(round(float(element[field] or 0.0), 2), precision_digits=2)

        output = StringIO()
        writer = csv.DictWriter(output, delimiter="|", skipinitialspace=True, lineterminator='\n', fieldnames=[*data[0], object()])
        writer.writerows(data)
        txt_result = output.getvalue()
        return txt_result
