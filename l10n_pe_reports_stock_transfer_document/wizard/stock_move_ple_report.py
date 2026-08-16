import csv
from io import StringIO

from odoo import models
from odoo.tools import float_repr


class L10n_PeStockPleWizard(models.TransientModel):
    _inherit = 'l10n_pe.stock.ple.wizard'

    # ------------------------------------------------------------------
    # Value variances (soft-guarded: the model lives in another module)
    # ------------------------------------------------------------------
    def _l10n_pe_move_variances(self, move):
        """Live variances of a movement, or an empty recordset when absent.

        Guarded on the model rather than on a field: without
        ``stock_landed_cost_variance`` installed the model does not exist at
        all, and a field check would raise instead of degrading.
        """
        if 'stock.value.variance' not in self.env:
            return self.env['stock.move'].browse()
        return self.env['stock.value.variance'].sudo().search([
            ('move_id', '=', move.id),
            ('absorbed', '=', False),
        ], order='date, id')

    def _l10n_pe_variance_adjustment_vals(self, variance):
        """Shape a variance as an adjustment line for ``_build_adjustment_line``.

        Its own CUO namespace: the base uses the move id, the landed-cost bridge
        ``{id}LC`` and the openings ``{id}A1``, so a fourth is needed or two
        lines of the same file would share a CUO.

        Operation type 99 ("Otros"). The catalogue Odoo ships has no code for a
        value adjustment -- 26/27 are production-service entry/exit and 28 is an
        inventory *quantity* difference -- and the increase line already emits 26
        natively, which is not ours to change without regressing the standard.
        """
        serie_folio = self._get_serie_folio(
            variance.landed_cost_line_id.cost_id.name
            or variance.account_move_id.name or '')
        return {
            'cuo': f'{variance.id}VA'.zfill(6),
            'value': variance.ledger_amount,
            'operation_type': '99',
            'date': variance.date.strftime('%d/%m/%Y'),
            'document_type': '00',
            'serie': serie_folio['serie'].replace(' ', '').replace('/', '') or '0',
            'folio': serie_folio['folio'].replace(' ', '') or '0',
        }

    def _l10n_pe_opening_variance(self, products):
        """Signed variance effect accrued before the period, per product.

        The opening balance is rebuilt from ``stock.move`` alone, and
        ``move.value`` carries the whole revaluation.  Without this the period
        would close on the corrected number and the next one would open on the
        uncorrected one -- a ledger that is wrong today at least stays
        continuous, and a discontinuous one is worse.
        """
        if 'stock.value.variance' not in self.env:
            return {}
        # Accrued by the date of the movement it belongs to, NOT by its own.
        # The body emits a variance inside the period of its parent movement --
        # a landed cost booked in March against a January receipt prints in the
        # January file -- so the opening has to use the same window. Splitting
        # the two would leave a gap at every boundary: the period would close
        # on the corrected figure and the next open on the uncorrected one,
        # with no line to explain the jump.
        domain = [
            ('company_id', '=', self.env.company.id),
            ('absorbed', '=', False),
            ('move_id.date', '<', self.date_from),
        ]
        if products:
            domain.append(('product_id', 'in', products))
        groups = self.env['stock.value.variance'].sudo()._read_group(
            domain, ['product_id'], ['ledger_amount:sum'])
        return {product.id: amount for product, amount in groups}

    # ------------------------------------------------------------------
    # Opening balances
    # ------------------------------------------------------------------
    def _l10n_pe_apply_opening_variance(self, rows, report):
        """Fold the variances accrued before the period into an opening row.

        Both opening builders live in the native module and rebuild the balance
        from ``stock.move`` alone, where ``move.value`` still carries the whole
        revaluation.  Left alone, a period would close on the corrected figure
        and the next one open on the uncorrected one.

        The product is recovered from the CUO, which the native code builds
        deterministically as ``f'{product.id}A1'.zfill(6)`` in both builders.  A
        row whose CUO does not parse is left untouched rather than guessed at.
        """
        if report == '1201' or not rows:
            # 12.1 carries physical units only; a value variance has none.
            return rows
        variance_by_product = self._l10n_pe_opening_variance(None)
        if not variance_by_product:
            return rows
        for row in rows:
            cuo = (row.get('cuo') or '').lstrip('0')
            if not cuo.endswith('A1'):
                continue
            try:
                product_id = int(cuo[:-2])
            except ValueError:
                continue
            amount = variance_by_product.get(product_id)
            if not amount:
                continue
            quantity = row.get('remaining', 0)
            value = row.get('value', 0) + amount
            row.update(self._valuation_columns(
                quantity, value, quantity, value, is_balance=True))
        return rows

    def _append_valuation_line(self, move, period, report):
        values = super()._append_valuation_line(move, period, report)
        if not values:
            return values
        return self._l10n_pe_apply_opening_variance([values], report)[0]

    def _append_historic_valuation_lines(self, products, period, report):
        rows = super()._append_historic_valuation_lines(products, period, report)
        return self._l10n_pe_apply_opening_variance(rows, report)

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
            date = (invoice.invoice_date or bill.invoice_date or move.date)
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
            # INJECTION 3 (soft-guarded): value variances recorded for this
            # movement by stock_landed_cost_variance. An adjustment on an
            # OUTGOING move is the corrected exit cost itself, so it is folded
            # into the line; on an INCOMING one it must NOT be, because folding
            # would restate the acquisition cost and the line would print a
            # unit cost the goods never had.
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

            # INJECTION 3 continued: the part of the revaluation that belongs to
            # goods already gone leaves as its own line, so the running balance
            # closes on what the stock is really worth.
            for variance in variances:
                balance[1] += variance.ledger_amount
                data.append(self._build_adjustment_line(
                    move, product, period,
                    self._l10n_pe_variance_adjustment_vals(variance), balance))
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
