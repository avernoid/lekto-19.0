# Part of the Ganemo product_variant_import_toolkit module.
# Wraps Odoo 19's native variant import (`import_attribute_values`) and adds
# capabilities the core leaves out, every one of them validated live against a
# 19.0 database before being written here:
#   1. External ID for template AND variant in a single file (native only does
#      the variant one, or forces a two-pass import for the template).
#   2. Claim by combination: bind an existing variant (even archived, even one
#      Odoo auto-generated without an external ID) to your external ID instead
#      of colliding on `product_product_combination_unique`.
#   3. price_extra per attribute value, imported from the same file.
#   4. Freeze: add native attribute exclusions so combinations absent from the
#      file are not auto-generated later (the correct, persistent mechanism).

import base64
import csv
import io
from collections import defaultdict

from markupsafe import Markup, escape

from odoo import _, fields, models
from odoo.exceptions import UserError

# Columns that carry structural meaning; everything else in the header is passed
# through verbatim to the native `product.template.load` (default_code, barcode,
# standard_price, list_price, categ_id, is_storable, weight, volume, ...).
STRUCTURAL_COLS = {'id', 'template_id', 'name', 'import_attribute_values'}
PRICE_EXTRA_PREFIX = 'price_extra:'


class ProductVariantImport(models.TransientModel):
    _name = 'product.variant.import'
    _description = "Variant Import Toolkit"

    data_file = fields.Binary(
        string="File (CSV)", required=True,
        help="The CSV file to import. Required columns: 'name' and "
             "'import_attribute_values'. Optional columns: 'id' (variant External "
             "ID), 'template_id' (template External ID), any product field "
             "(default_code, barcode, standard_price, list_price, categ_id, "
             "is_storable...) and 'price_extra:<Attribute>' for value-level extra "
             "prices.")
    filename = fields.Char(
        string="Filename",
        help="Name of the uploaded file. Filled automatically by the upload "
             "widget; it does not affect the import.")
    delimiter = fields.Selection(
        selection=[('comma', "Comma  ,"), ('semicolon', "Semicolon  ;"), ('tab', "Tab")],
        string="Delimiter", default='comma', required=True,
        help="Character that separates the columns in your file. Choose the one "
             "your export uses (comma, semicolon or tab) so the columns are read "
             "correctly.")
    encoding = fields.Char(
        string="Encoding", default='utf-8', required=True,
        help="Text encoding used to read the file (e.g. 'utf-8' or 'latin-1'). "
             "Use 'utf-8' unless your file was exported with a different one, "
             "otherwise accented characters may be misread.")
    module_prefix = fields.Char(
        string="Module Prefix", default='__import__', required=True,
        help="Module part applied to External IDs written without a dot: "
             "'sku_polo' becomes '<prefix>.sku_polo'. Values that already contain "
             "a dot (e.g. 'ganemo.sku_polo') are used as-is.")
    assign_template_xmlid = fields.Boolean(
        string="External ID for templates", default=True,
        help="Create an external ID for each template from the 'template_id' "
             "column, so templates are addressable in future imports. Native "
             "import only assigns external IDs to variants.")
    claim_existing = fields.Boolean(
        string="Claim existing variants", default=True,
        help="If a variant for a combination already exists (even archived, "
             "even auto-generated without an external ID), reactivate it and "
             "bind your external ID instead of failing with a duplicate-"
             "combination error.")
    freeze_others = fields.Boolean(
        string="Freeze non-imported combinations", default=False,
        help="Add native attribute exclusions so the combinations that are NOT "
             "in this file are not auto-generated when the template is edited "
             "later. Exclusions are pairwise: with 3+ attributes some "
             "combinations cannot be isolated; those are reported, not frozen.")
    state = fields.Selection([('draft', "Draft"), ('done', "Done")], default='draft')
    result_html = fields.Html(
        string="Import Report", readonly=True,
        help="Summary shown after the import: variants created, variants claimed, "
             "External IDs added, price_extra set, exclusions added, and any "
             "combination the freeze could not isolate.")

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------
    def _read_rows(self):
        self.ensure_one()
        if not self.data_file:
            raise UserError(_("Please attach a CSV file."))
        raw = base64.b64decode(self.data_file)
        try:
            text = raw.decode(self.encoding or 'utf-8')
        except (UnicodeDecodeError, LookupError) as e:
            raise UserError(_("Could not decode the file with encoding %s: %s", self.encoding, e))
        delim = {'comma': ',', 'semicolon': ';', 'tab': '\t'}[self.delimiter]
        reader = csv.reader(io.StringIO(text), delimiter=delim)
        table = [row for row in reader]
        if not table:
            raise UserError(_("The file is empty."))
        header = [h.strip() for h in table[0]]
        if 'name' not in header or 'import_attribute_values' not in header:
            raise UserError(_(
                "The file must have at least the columns 'name' and "
                "'import_attribute_values'."))
        rows = [dict(zip(header, r)) for r in table[1:] if any((c or '').strip() for c in r)]
        return header, rows

    def _split_xmlid(self, ext_id):
        ext_id = (ext_id or '').strip()
        if not ext_id:
            return None, None
        if '.' in ext_id:
            module, name = ext_id.split('.', 1)
        else:
            module, name = self.module_prefix, ext_id
        return module.strip(), name.strip()

    def _ensure_xmlid(self, record, ext_id, report):
        """Attach an external ID to `record` if it has none. Never overwrites an
        existing external ID (that would be unsafe for module-owned records)."""
        module, name = self._split_xmlid(ext_id)
        if not module:
            return
        IMD = self.env['ir.model.data']
        current = IMD.search([('model', '=', record._name), ('res_id', '=', record.id)], limit=1)
        if current:
            if (current.module, current.name) != (module, name):
                report['xmlid_kept'].append(
                    "%s: keeps %s.%s (asked %s.%s)"
                    % (record.display_name, current.module, current.name, module, name))
            return
        clash = IMD.search([('module', '=', module), ('name', '=', name)], limit=1)
        if clash and not (clash.model == record._name and clash.res_id == record.id):
            raise UserError(_(
                "External ID %(m)s.%(n)s already points to another record (%(model)s #%(rid)s).",
                m=module, n=name, model=clash.model, rid=clash.res_id))
        IMD.create({
            'module': module, 'name': name,
            'model': record._name, 'res_id': record.id, 'noupdate': True,
        })
        report['xmlid_new'] += 1

    def _parse_combo(self, combo_str):
        """'Size:S,Color:Red' -> {'Size': 'S', 'Color': 'Red'} (ordered by input)."""
        out = {}
        for token in (combo_str or '').split(','):
            if ':' in token:
                attr, val = token.split(':', 1)
                out[attr.strip()] = val.strip()
        return out

    def _resolve_combo_ptavs(self, template, combo_str):
        """Return the `product.template.attribute.value` recordset for a combo on
        `template`, or None if any value is not (yet) defined on the template."""
        PTAV = self.env['product.template.attribute.value']
        ptavs = PTAV.browse()
        combo = self._parse_combo(combo_str)
        if not combo:
            return None
        for attr, val in combo.items():
            ptav = PTAV.search([
                ('product_tmpl_id', '=', template.id),
                ('attribute_id.name', '=', attr),
                ('product_attribute_value_id.name', '=', val),
            ], limit=1)
            if not ptav:
                return None
            ptavs |= ptav
        return ptavs

    def _variant_write_vals(self, row, header):
        """Passthrough variant-level fields for a claimed variant (write directly,
        since claimed rows skip the native load)."""
        Product = self.env['product.product']
        vals = {}
        for col in header:
            if col in STRUCTURAL_COLS or col.startswith(PRICE_EXTRA_PREFIX):
                continue
            value = (row.get(col) or '').strip()
            if not value or col not in Product._fields:
                continue
            field = Product._fields[col]
            try:
                if field.type in ('float', 'monetary'):
                    vals[col] = float(value)
                elif field.type == 'integer':
                    vals[col] = int(value)
                elif field.type == 'boolean':
                    vals[col] = value.lower() in ('1', 'true', 'vrai', 'verdadero', 'yes')
                else:
                    vals[col] = value
            except ValueError:
                continue
        return vals

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def action_import(self):
        self.ensure_one()
        header, rows = self._read_rows()
        report = defaultdict(list)
        report['xmlid_new'] = 0

        # Phase A -- Claim. For rows whose template AND combination already exist,
        # reactivate + bind the external ID here, and drop them from the native
        # load batch so they cannot collide on the combination unique index.
        rows_to_load = []
        for row in rows:
            name = (row.get('name') or '').strip()
            combo = (row.get('import_attribute_values') or '').strip()
            claimed = False
            if self.claim_existing and name and combo:
                template = self._find_template(row)
                if template:
                    ptavs = self._resolve_combo_ptavs(template, combo)
                    if ptavs is not None and len(ptavs) == len(self._parse_combo(combo)):
                        variant = self.env['product.product'].with_context(
                            active_test=False).search([
                                ('product_tmpl_id', '=', template.id),
                                ('combination_indices', '=', ptavs._ids2str()),
                            ], limit=1)
                        if variant:
                            self._claim_variant(variant, row, header, report)
                            claimed = True
            if not claimed:
                rows_to_load.append(row)

        # Phase B -- native import for the remaining (new) variants. The `id`
        # column makes the core assign the variant external IDs for us.
        load_messages = []
        if rows_to_load:
            load_messages = self._run_native_load(header, rows_to_load, report)

        # Phase C -- template external IDs (native import never assigns these).
        if self.assign_template_xmlid:
            self._assign_template_xmlids(rows, report)

        # Phase D -- price_extra per attribute value.
        self._apply_price_extra(header, rows, report)

        # Phase E -- freeze non-imported combinations via native exclusions.
        if self.freeze_others:
            self._freeze(rows, report)

        self.state = 'done'
        self.result_html = self._render_report(report, load_messages)
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    # ------------------------------------------------------------------
    # Phases
    # ------------------------------------------------------------------
    def _find_template(self, row):
        """Locate the template for a row: by 'template_id' external ID first, then
        by exact name."""
        ext = (row.get('template_id') or '').strip()
        if ext:
            rec = self.env.ref(ext, raise_if_not_found=False)
            if rec and rec._name == 'product.template':
                return rec
        name = (row.get('name') or '').strip()
        if name:
            return self.env['product.template'].search([('name', '=', name)], limit=1)
        return self.env['product.template']

    def _claim_variant(self, variant, row, header, report):
        if not variant.active:
            variant.active = True
        vals = self._variant_write_vals(row, header)
        if vals:
            variant.write(vals)
        ext = (row.get('id') or '').strip()
        if ext:
            self._ensure_xmlid(variant, ext, report)
        report['claimed'].append(variant.display_name)

    def _run_native_load(self, header, rows, report):
        # Only forward columns the native product import understands: drop our
        # own custom columns (template_id, price_extra:<Attr>). Normalise the id
        # column to a fully-qualified module.name so our module_prefix is honoured
        # (the core would otherwise force '__import__').
        load_cols = [c for c in header
                     if c != 'template_id' and not c.startswith(PRICE_EXTRA_PREFIX)]
        data = []
        for row in rows:
            line = []
            for col in load_cols:
                value = row.get(col) or ''
                if col == 'id' and value.strip():
                    module, name = self._split_xmlid(value)
                    value = '%s.%s' % (module, name)
                line.append(value)
            data.append(line)
        result = self.env['product.template'].load(load_cols, data)
        messages = [m for m in result.get('messages', []) if m.get('type') == 'error']
        # `load` returns template ids; count the variant rows we actually sent
        # (minus the rows the core rejected) so the report is honest.
        report['created'] = max(len(data) - len(messages), 0)
        return messages

    def _assign_template_xmlids(self, rows, report):
        seen = {}
        for row in rows:
            name = (row.get('name') or '').strip()
            ext = (row.get('template_id') or '').strip()
            if name and ext and name not in seen:
                seen[name] = ext
        for name, ext in seen.items():
            template = self.env['product.template'].search([('name', '=', name)], limit=1)
            if template:
                self._ensure_xmlid(template, ext, report)

    def _apply_price_extra(self, header, rows, report):
        pe_cols = [c for c in header if c.startswith(PRICE_EXTRA_PREFIX)]
        if not pe_cols:
            return
        PTAV = self.env['product.template.attribute.value']
        for row in rows:
            template = self._find_template(row)
            if not template:
                continue
            combo = self._parse_combo(row.get('import_attribute_values'))
            for col in pe_cols:
                raw = (row.get(col) or '').strip()
                if not raw:
                    continue
                attr = col[len(PRICE_EXTRA_PREFIX):].strip()
                val = combo.get(attr)
                if not val:
                    continue
                ptav = PTAV.search([
                    ('product_tmpl_id', '=', template.id),
                    ('attribute_id.name', '=', attr),
                    ('product_attribute_value_id.name', '=', val),
                ], limit=1)
                if not ptav:
                    continue
                try:
                    price = float(raw)
                except ValueError:
                    continue
                if ptav.price_extra != price:
                    ptav.price_extra = price
                    report['price_extra'].append("%s = %s" % (ptav.display_name, price))

    def _freeze(self, rows, report):
        Exclusion = self.env['product.template.attribute.exclusion']
        # Group imported combinations per template.
        combos_by_tmpl = defaultdict(list)
        for row in rows:
            template = self._find_template(row)
            if not template:
                continue
            ptavs = self._resolve_combo_ptavs(template, row.get('import_attribute_values'))
            if ptavs:
                combos_by_tmpl[template.id].append(set(ptavs.ids))

        for tmpl_id, combos in combos_by_tmpl.items():
            template = self.env['product.template'].browse(tmpl_id)
            if not combos:
                continue
            # Every value pair that co-occurs in at least one imported combination.
            cooccurring = set()
            for combo in combos:
                ids = sorted(combo)
                for i, a in enumerate(ids):
                    for b in ids[i + 1:]:
                        cooccurring.add(frozenset((a, b)))
            imported = {frozenset(c) for c in combos}

            lines = template.valid_product_template_attribute_line_ids
            existing = {
                (e.product_template_attribute_value_id.id, tuple(sorted(e.value_ids.ids)))
                for e in template.attribute_line_ids.product_template_value_ids.exclude_for
            }
            new_exclusions = []
            line_list = list(lines)
            for i, li in enumerate(line_list):
                for lj in line_list[i + 1:]:
                    for a in li.product_template_value_ids._only_active():
                        excluded = [
                            b.id for b in lj.product_template_value_ids._only_active()
                            if frozenset((a.id, b.id)) not in cooccurring
                        ]
                        if excluded and (a.id, tuple(sorted(excluded))) not in existing:
                            new_exclusions.append({
                                'product_tmpl_id': template.id,
                                'product_template_attribute_value_id': a.id,
                                'value_ids': [(6, 0, excluded)],
                            })
            if new_exclusions:
                Exclusion.create(new_exclusions)
                report['frozen'].append("%s: +%d exclusion(s)" % (template.display_name, len(new_exclusions)))

            # Residuals: combinations that pairwise exclusions could not isolate
            # (only happens with 3+ attributes). They remain active; report them.
            residual = [
                v.display_name for v in template.product_variant_ids
                if set(v.product_template_attribute_value_ids.ids) not in imported
            ]
            if residual:
                report['residual'].extend(residual)

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------
    def _render_report(self, report, load_messages):
        def section(title, items):
            if not items:
                return Markup('')
            lis = Markup('').join(Markup('<li>%s</li>') % escape(i) for i in items)
            return Markup('<h4>%s</h4><ul>%s</ul>') % (title, lis)

        out = Markup('<div><p><b>%d</b> variant row(s) imported, <b>%d</b> claimed, '
                     '<b>%d</b> external ID(s) added.</p>') % (
            report.get('created', 0), len(report.get('claimed', [])), report.get('xmlid_new', 0))
        if load_messages:
            errors = Markup('').join(
                Markup('<li>%s</li>') % escape(m.get('message', '')) for m in load_messages)
            out += Markup('<h4 style="color:#b00">Errors from native import</h4><ul>%s</ul>') % errors
        out += section(_("Claimed variants"), report.get('claimed'))
        out += section(_("price_extra set"), report.get('price_extra'))
        out += section(_("Frozen (exclusions added)"), report.get('frozen'))
        out += section(_("External IDs kept (not overwritten)"), report.get('xmlid_kept'))
        out += section(
            _("Residual combinations (pairwise exclusions could not isolate — use "
              "Variant Archive Lock or archive manually)"), report.get('residual'))
        return out + Markup('</div>')
