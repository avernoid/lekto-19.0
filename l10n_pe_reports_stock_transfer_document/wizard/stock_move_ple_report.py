import csv
from io import StringIO

from odoo import models
from odoo.tools import float_repr


class L10n_PeStockPleWizard(models.TransientModel):
    _inherit = 'l10n_pe.stock.ple.wizard'

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
