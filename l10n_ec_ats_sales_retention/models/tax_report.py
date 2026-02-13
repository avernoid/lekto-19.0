# -*- coding: utf-8 -*-
# Part of l10n_ec_ats_sales_retention. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class L10nECTaxReportATSCustomHandler(models.AbstractModel):
    _inherit = 'account.tax.report.handler'

    @api.model
    def _get_sales_info_by_partner(self, invoices_values):
        """Override to calculate actual valorRetIva and valorRetRenta
        from customer withholdings (out_withhold) linked to sale invoices."""
        group_sales, errors = super()._get_sales_info_by_partner(invoices_values)

        # Proactive protection: if Odoo natively fixes the bug in a future
        # version, super() will already return non-zero retention values.
        # In that case, skip our calculation to avoid duplicating amounts.
        already_calculated = any(
            vals.get('valorRetIva', 0.0) != 0.0 or vals.get('valorRetRenta', 0.0) != 0.0
            for vals in group_sales.values()
        )
        if already_calculated:
            return group_sales, errors

        # Build a mapping: invoice_id -> group key used in group_sales
        # The group key is (commercial_partner, latam_document_type_code, tipoEmision)
        all_move_ids = []
        move_id_to_key = {}
        for inv_vals in invoices_values:
            move = inv_vals['move']
            key = (
                move.partner_id.commercial_partner_id,
                inv_vals['latam_document_type_code'],
                inv_vals['tipoEmision'],
            )
            all_move_ids.append(move.id)
            move_id_to_key[move.id] = key

        if not all_move_ids:
            return group_sales, errors

        # Find all posted out_withhold tax lines linked to these sale invoices
        withhold_tax_lines = self.env['account.move.line'].search([
            ('l10n_ec_withhold_invoice_id', 'in', all_move_ids),
            ('tax_line_id', '!=', False),
            ('parent_state', '=', 'posted'),
            ('tax_line_id.tax_group_id.l10n_ec_type', 'in',
             ['withhold_vat_sale', 'withhold_income_sale']),
        ])

        # Accumulate retention amounts by group key
        for wh_line in withhold_tax_lines:
            invoice_id = wh_line.l10n_ec_withhold_invoice_id.id
            key = move_id_to_key.get(invoice_id)
            if key and key in group_sales:
                amount = abs(wh_line.balance)
                ec_type = wh_line.tax_line_id.tax_group_id.l10n_ec_type
                if ec_type == 'withhold_vat_sale':
                    group_sales[key]['valorRetIva'] += amount
                elif ec_type == 'withhold_income_sale':
                    group_sales[key]['valorRetRenta'] += amount

        return group_sales, errors
