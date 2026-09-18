from odoo import fields, models

# A GTIN is numeric and 8, 12, 13 or 14 digits long; a SUNAT product code
# (UNSPSC) is numeric and exactly 8.  Used to spot a catalogue that does not
# match the code it declares -- in both directions.
GTIN_LENGTHS = (8, 12, 13, 14)
UNSPSC_LENGTH = 8

# Table 5 codes whose entries and exits carry the conditional obligation to
# report fields 8/9: merchandise and finished products.
GOODS_EXISTENCE_TYPES = ('1', '2')

# Per finding kind, so a database with thousands of unpicked movements does not
# build a list nobody can read.  What is dropped is reported, never silently.
FINDING_CAP = 100


class L10nPeStockPleAuditLine(models.TransientModel):
    _name = 'l10n_pe.stock.ple.audit.line'
    _description = 'Peruvian Kardex PLE Audit Finding'
    _order = 'severity, kind, product_id'

    kind = fields.Selection(
        [
            ('missing_code', 'Existence code empty (field 7)'),
            ('missing_uom_code', 'Unit of measure without SUNAT code (field 16)'),
            ('date_out_of_period', 'Document date outside the period (field 10)'),
            ('catalogue_mismatch', 'Catalogue does not match the code (field 5)'),
            ('missing_existence_type', 'Type of existence not set (field 6)'),
            ('missing_unspsc', 'Goods without UNSPSC code (fields 8/9)'),
            ('no_picking', 'Movement without a transfer (fields 4 and 14)'),
            ('capped', 'Findings not listed'),
        ],
        string='Finding', readonly=True)
    severity = fields.Selection(
        [
            ('rejected', 'Rejected by SUNAT'),
            ('warning', 'Warning'),
        ],
        string='Severity', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    move_id = fields.Many2one('stock.move', string='Movement', readonly=True)
    detail = fields.Char(string='Detail', readonly=True)

    def action_l10n_pe_ple_back_to_report(self):
        """Reopen the emission wizard the audit was launched from.

        The audit replaces the wizard dialog, so without this the chosen period
        would be lost and the user would have to type it again.  Falls back to a
        fresh wizard if the transient record is already gone.
        """
        wizard = self.env['l10n_pe.stock.ple.wizard'].browse(
            self.env.context.get('ple_wizard_id') or []).exists()
        if not wizard:
            wizard = self.env['l10n_pe.stock.ple.wizard'].create({})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_pe.stock.ple.wizard',
            'res_id': wizard.id,
            'views': [(self.env.ref(
                'l10n_pe_reports_stock.view_l10n_pe_stock_ple_wizard').id, 'form')],
            'target': 'new',
        }


class L10n_PeStockPleWizard(models.TransientModel):
    _inherit = 'l10n_pe.stock.ple.wizard'

    # ------------------------------------------------------------------
    # Audit -- never blocking, never writes anything to the data.
    # ------------------------------------------------------------------
    def action_l10n_pe_ple_audit(self):
        """Report what would make SUNAT reject or observe the file.

        Read-only by design: it neither fills defaults nor stops the emission,
        because a wrong default produces a file that passes validation carrying
        the wrong data, which is worse than a rejection.
        """
        self.ensure_one()
        findings = self._l10n_pe_ple_audit_findings()
        if not findings:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'title': self.env._('Audit clean'),
                    'message': self.env._(
                        'No finding on the movements of the chosen period.'),
                    'next': {'type': 'ir.actions.act_window_close'},
                },
            }
        lines = self.env['l10n_pe.stock.ple.audit.line'].create(findings)
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('PLE Audit'),
            'res_model': 'l10n_pe.stock.ple.audit.line',
            'view_mode': 'list',
            'views': [(self.env.ref(
                'l10n_pe_reports_stock_transfer_document.'
                'l10n_pe_stock_ple_audit_line_list').id, 'list')],
            'domain': [('id', 'in', lines.ids)],
            # ple_wizard_id lets the "Back to the report" button of the list
            # reopen THIS wizard, with the period the user already chose.
            'context': {'group_by': 'kind', 'ple_wizard_id': self.id},
            'target': 'new',
        }

    def _l10n_pe_ple_audit_findings(self):
        """Build the finding values for the movements of the period."""
        self.ensure_one()
        moves = self._get_ple_reports_data()
        period = (self.date_from.year, self.date_from.month)
        findings = []
        counts = {}
        dropped = {}
        seen_products = set()
        seen_uoms = set()

        def add(kind, severity, detail, product=None, move=None):
            counts[kind] = counts.get(kind, 0) + 1
            if counts[kind] > FINDING_CAP:
                dropped[kind] = dropped.get(kind, 0) + 1
                return
            findings.append({
                'kind': kind,
                'severity': severity,
                'detail': detail,
                'product_id': product.id if product else False,
                'move_id': move.id if move else False,
            })

        for move in moves:
            product = move.product_id

            if not move.picking_id:
                add('no_picking', 'warning', self.env._(
                    'Without a transfer the establishment is reported as 0000 '
                    'and the type of operation as 99.'), product, move)

            document = (
                move.sale_line_id.invoice_lines.move_id.sorted('id')[:1]
                or move.purchase_line_id.invoice_lines.move_id.sorted('id')[:1]
            )
            if document.invoice_date and (
                    document.invoice_date.year,
                    document.invoice_date.month) > period:
                add('date_out_of_period', 'warning', self.env._(
                    'Document %(name)s is dated %(date)s, later than the '
                    'period; the movement date is reported instead.',
                    name=document.name or '',
                    date=document.invoice_date.strftime('%d/%m/%Y'),
                ), product, move)

            uom = move.product_uom
            if not uom.l10n_pe_edi_measure_unit_code and uom.id not in seen_uoms:
                seen_uoms.add(uom.id)
                add('missing_uom_code', 'rejected', self.env._(
                    'Unit of measure %(uom)s has no SUNAT code (Table 6).',
                    uom=uom.display_name,
                ), product, move)

            if product.id in seen_products:
                continue
            seen_products.add(product.id)
            findings_for_product = self._l10n_pe_ple_audit_product(product)
            for kind, severity, detail in findings_for_product:
                add(kind, severity, detail, product)

        for kind, missing in dropped.items():
            findings.append({
                'kind': 'capped',
                'severity': 'warning',
                'detail': self.env._(
                    '%(count)s more findings of type "%(kind)s" are not listed.',
                    count=missing, kind=kind),
            })
        return findings

    def _l10n_pe_ple_audit_product(self, product):
        """Findings that depend on the product master data only."""
        template = product.product_tmpl_id
        code = product._l10n_pe_ple_existence_code()
        catalogue = template.l10n_pe_existence_catalogue or '9'
        source = template.l10n_pe_existence_code_source or 'internal_reference'
        result = []

        if not code:
            # 'source' is the name of Environment._'s own first parameter:
            # passing it as a keyword raises TypeError.
            result.append(('missing_code', 'rejected', self.env._(
                'The chosen source (%(field)s) is empty, so field 7 goes '
                'empty and SUNAT rejects the file.', field=source)))
        else:
            looks_numeric = code.isdigit()
            if catalogue == '3' and not (looks_numeric and len(code) in GTIN_LENGTHS):
                result.append(('catalogue_mismatch', 'warning', self.env._(
                    'Catalogue 3 (GTIN) declared for %(code)s, which is not a '
                    'GTIN (8, 12, 13 or 14 digits).', code=code)))
            elif catalogue == '1' and not (looks_numeric and len(code) == UNSPSC_LENGTH):
                result.append(('catalogue_mismatch', 'warning', self.env._(
                    'Catalogue 1 (United Nations) declared for %(code)s, which '
                    'is not an 8 digit UNSPSC code.', code=code)))
            elif catalogue == '9' and looks_numeric and len(code) in GTIN_LENGTHS:
                result.append(('catalogue_mismatch', 'warning', self.env._(
                    '%(code)s looks like a GTIN or a UNSPSC code but is '
                    'declared as catalogue 9 (Others).', code=code)))

        existence_type = template.l10n_pe_type_of_existence
        if not existence_type:
            result.append(('missing_existence_type', 'warning', self.env._(
                'Field 6 will be reported as 99 (Others).')))
        elif existence_type in GOODS_EXISTENCE_TYPES and not template.unspsc_code_id:
            result.append(('missing_unspsc', 'warning', self.env._(
                'Merchandise and finished products must report fields 8/9 when '
                'the electronic invoice carries the UNSPSC or GTIN code.')))
        return result
