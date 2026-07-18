import logging
from datetime import datetime

from odoo import api, models

_logger = logging.getLogger(__name__)

# Every demo document happens in this year, spread over Jan-Jun so a single
# glance at the Product Moves list (or one wizard run) shows a realistic history.
_YEAR = 2026

# Runs the generation at most once (the demo <function> would otherwise re-run
# on every module update).
_DEMO_FLAG = 'invoice_type_document_extension.demo_generated'

# ---------------------------------------------------------------------------
# Realistic, 100% SYNTHETIC catalogue.  Products are referenced by the XML ids
# declared in data/demo/invoice_type_document_extension_demo.xml.
# (vendor/customer keys map to the partner XML ids there too.)
# ---------------------------------------------------------------------------

# Purchases.  Each spec = one vendor receipt (+ its vendor bill) whose FINAL
# state teaches one case.  ``mode`` drives the post-processing:
#   'auto'            receipt + posted bill -> filled automatically (the norm).
#   'empty_derivable' filled then cleared -> EMPTY but a posted bill still backs
#                     it, so "Fill empty"/"Re-derive" will fill it live.
#   'stale'           filled then value corrupted (non-manual) -> "Re-derive"
#                     fixes it; the count of "would change" picks it up.
#   'manual'          filled, then hand-edited (manual_override) with a DIFFERENT
#                     number -> protected from "Re-derive" unless include_manual.
#   'legacy'          receipt with NO bill (stays empty) but the legacy value is
#                     stored on the picking -> "Recover serie/number" fills it.
#   'draft_bill'      receipt + UNPOSTED bill -> empty, nothing to derive yet.
#   'noprefix'        posted bill whose type has no series prefix -> the number
#                     posts as 'False ...' and is discarded -> stays empty.
_PURCHASES = [
    # --- the realistic steady state: many correctly captured receipts --------
    {'v': 'vendor_tecnoandes', 'd': '01-04', 'n': 'F001-00004521', 'type': 'factura',
     'lines': [('laptop', 8, 2800.0), ('ssd', 20, 260.0)], 'mode': 'auto'},
    {'v': 'vendor_norte', 'd': '01-09', 'n': 'F150-00000812', 'type': 'factura',
     'lines': [('monitor', 15, 620.0)], 'mode': 'auto'},
    {'v': 'vendor_global', 'd': '01-15', 'n': 'F001-00021044', 'type': 'factura',
     'lines': [('silla', 30, 240.0), ('escritorio', 12, 410.0)], 'mode': 'auto'},
    {'v': 'vendor_tecnoandes', 'd': '02-03', 'n': 'F001-00004689', 'type': 'factura',
     'lines': [('teclado', 40, 95.0), ('mouse', 40, 38.0)], 'mode': 'auto'},
    {'v': 'vendor_norte', 'd': '02-18', 'n': 'F150-00000934', 'type': 'factura',
     'lines': [('impresora', 10, 780.0)], 'mode': 'auto'},
    {'v': 'vendor_global', 'd': '03-07', 'n': 'F001-00021399', 'type': 'factura',
     'lines': [('laptop', 6, 2790.0), ('monitor', 10, 615.0)], 'mode': 'auto'},
    {'v': 'vendor_tecnoandes', 'd': '04-02', 'n': 'F001-00004921', 'type': 'factura',
     'lines': [('ssd', 25, 255.0)], 'mode': 'auto'},
    {'v': 'vendor_norte', 'd': '05-06', 'n': 'F150-00001178', 'type': 'factura',
     'lines': [('silla', 20, 245.0)], 'mode': 'auto'},
    # --- teaching cases for the wizard ---------------------------------------
    {'v': 'vendor_global', 'd': '01-22', 'n': 'F001-00021102', 'type': 'factura',
     'lines': [('escritorio', 8, 415.0)], 'mode': 'empty_derivable'},
    {'v': 'vendor_tecnoandes', 'd': '02-25', 'n': 'F001-00004777', 'type': 'factura',
     'lines': [('teclado', 15, 96.0)], 'mode': 'empty_derivable'},
    {'v': 'vendor_norte', 'd': '03-14', 'n': 'F150-00001002', 'type': 'factura',
     'lines': [('monitor', 5, 630.0)], 'mode': 'stale'},
    {'v': 'vendor_global', 'd': '03-28', 'n': 'F001-00021520', 'type': 'factura',
     'lines': [('mouse', 25, 39.0)], 'mode': 'stale'},
    {'v': 'vendor_tecnoandes', 'd': '04-16', 'n': 'F001-00005040', 'type': 'factura',
     'lines': [('laptop', 4, 2810.0)], 'mode': 'manual'},
    {'v': 'vendor_norte', 'd': '05-20', 'n': 'F150-00001260', 'type': 'factura',
     'lines': [('impresora', 6, 775.0)], 'mode': 'manual'},
    {'v': 'vendor_global', 'd': '02-11', 'n': 'F001-00021260', 'type': 'factura',
     'lines': [('ssd', 12, 258.0)], 'mode': 'legacy'},
    {'v': 'vendor_tecnoandes', 'd': '04-29', 'n': 'F001-00005111', 'type': 'factura',
     'lines': [('silla', 10, 243.0)], 'mode': 'legacy'},
    {'v': 'vendor_norte', 'd': '05-27', 'n': 'F150-00001305', 'type': 'factura',
     'lines': [('teclado', 8, 97.0)], 'mode': 'draft_bill'},
    {'v': 'vendor_global', 'd': '06-04', 'n': 'F001-00021740', 'type': 'noprefix',
     'lines': [('mouse', 10, 40.0)], 'mode': 'noprefix'},
]

# Sales (our own delivery + customer invoice).  Mostly correctly captured; a
# couple of teaching cases mirror the purchase side on the outgoing flow.
_SALES = [
    {'c': 'customer_sur', 'd': '01-11', 'n': 'F001-00000341', 'type': 'factura',
     'lines': [('laptop', 3, 3500.0), ('monitor', 3, 820.0)], 'mode': 'auto'},
    {'c': 'customer_pacifico', 'd': '01-24', 'n': 'F001-00000352', 'type': 'factura',
     'lines': [('silla', 12, 360.0)], 'mode': 'auto'},
    {'c': 'customer_oficentro', 'd': '02-07', 'n': 'F001-00000369', 'type': 'factura',
     'lines': [('escritorio', 5, 590.0), ('silla', 5, 360.0)], 'mode': 'auto'},
    {'c': 'customer_sur', 'd': '02-21', 'n': 'F001-00000388', 'type': 'factura',
     'lines': [('ssd', 10, 380.0), ('teclado', 10, 140.0)], 'mode': 'auto'},
    {'c': 'customer_pacifico', 'd': '03-12', 'n': 'F001-00000410', 'type': 'factura',
     'lines': [('monitor', 6, 830.0)], 'mode': 'auto'},
    {'c': 'customer_oficentro', 'd': '04-05', 'n': 'F001-00000441', 'type': 'factura',
     'lines': [('impresora', 4, 1050.0)], 'mode': 'auto'},
    {'c': 'customer_sur', 'd': '05-14', 'n': 'F001-00000472', 'type': 'factura',
     'lines': [('laptop', 2, 3480.0)], 'mode': 'auto'},
    {'c': 'customer_pacifico', 'd': '03-25', 'n': 'F001-00000423', 'type': 'factura',
     'lines': [('mouse', 15, 62.0)], 'mode': 'empty_derivable'},
    {'c': 'customer_oficentro', 'd': '05-29', 'n': 'F001-00000489', 'type': 'factura',
     'lines': [('teclado', 6, 145.0)], 'mode': 'stale'},
    {'c': 'customer_sur', 'd': '06-09', 'n': 'F001-00000501', 'type': 'factura',
     'lines': [('silla', 4, 365.0)], 'mode': 'manual'},
]

# Internal transfers (warehouse -> warehouse): no invoice, no guide -> they must
# stay EMPTY (the Kardex bridge then inherits the native behaviour).
_INTERNAL = [
    {'d': '02-14', 'lines': [('laptop', 2), ('ssd', 5)]},
    {'d': '03-30', 'lines': [('silla', 6)]},
    {'d': '05-11', 'lines': [('monitor', 3), ('teclado', 4)]},
]


class InvoiceTypeDocumentDemo(models.AbstractModel):
    """Programmatic generator for the didactic PLE-transfer-document demo.

    Captured moves must go through the real confirm/receive/deliver/post flow so
    the capture events fire exactly as in production; that cannot be expressed as
    flat XML.  Invoked once from data/demo via a ``<function>`` and idempotent
    (guarded by an ``ir.config_parameter`` flag).
    """
    _name = 'invoice.type.document.demo'
    _description = 'PLE transfer document demo generator'

    # -- entry point ---------------------------------------------------------
    @api.model
    def _generate_demo_data(self):
        icp = self.env['ir.config_parameter'].sudo()
        if icp.get_param(_DEMO_FLAG):
            return

        company = self.env.ref('base.main_company', raise_if_not_found=False)
        pe = self.env.ref('base.pe', raise_if_not_found=False)
        if not company or not pe:
            return
        warehouse = self.env['stock.warehouse'].search(
            [('company_id', '=', company.id)], limit=1)
        if not warehouse:
            _logger.info("itde demo: no warehouse for %s, skipped.", company.name)
            return

        gen = self.sudo().with_company(company).with_context(
            allowed_company_ids=[company.id])
        setup = gen._setup_company(company, pe)
        if not setup:
            _logger.info("itde demo: accounting not configured for %s, skipped.",
                         company.name)
            return

        ctx = {
            'company': company,
            'pe': pe,
            'warehouse': warehouse,
            'stock_loc': warehouse.lot_stock_id,
            'supplier_loc': self.env.ref('stock.stock_location_suppliers'),
            'customer_loc': self.env.ref('stock.stock_location_customers'),
            'types': gen._doc_types(pe),
            'sale_journal': setup['sale_journal'],
            'purchase_journal': setup['purchase_journal'],
        }

        built = 0
        for spec in _PURCHASES:
            built += bool(gen._run_purchase(ctx, spec))
        for spec in _SALES:
            built += bool(gen._run_sale(ctx, spec))
        for spec in _INTERNAL:
            built += bool(gen._run_internal(ctx, spec))
        # One purchase return + credit note (Nota de Crédito, in_refund): the
        # return move resolves its document from the credit note.
        gen._run_purchase_return(ctx)

        icp.set_param(_DEMO_FLAG, '1')
        _logger.info("itde demo: generated %s transfer-document scenarios.", built)

    # -- environment setup ---------------------------------------------------
    def _setup_company(self, company, pe):
        """Make the main company able to run the demo: Peruvian (so the LATAM
        capture gate passes), with dedicated document-using journals and income/
        expense accounts on the demo category so bills/invoices can post.

        Returns the demo journals, or None if no P&L accounts are configured
        (then the demo is skipped rather than crashing the install)."""
        if company.country_id != pe:
            company.sudo().write({'country_id': pe.id})

        Account = self.env['account.account']
        base = ([('company_ids', 'in', company.id)]
                if 'company_ids' in Account._fields
                else [('company_id', '=', company.id)])
        income = Account.search(
            base + [('account_type', 'in', ('income', 'income_other'))], limit=1)
        expense = Account.search(
            base + [('account_type', 'in', ('expense', 'expense_direct_cost'))],
            limit=1)
        if not income or not expense:
            return None

        categ = self.env.ref(
            'invoice_type_document_extension.categ_demo_itde',
            raise_if_not_found=False)
        if categ:
            categ.property_account_income_categ_id = income.id
            categ.property_account_expense_categ_id = expense.id

        # Dedicated journals created fresh (no validated invoices) so enabling
        # "use documents" is allowed -- the shared demo journals already carry
        # posted invoices and l10n_latam forbids toggling the flag on those.
        Journal = self.env['account.journal']
        use_docs = 'l10n_latam_use_documents' in Journal._fields

        def journal(jtype, code, name, account):
            existing = Journal.search(
                [('code', '=', code), ('company_id', '=', company.id)], limit=1)
            if existing:
                if use_docs and not existing.l10n_latam_use_documents:
                    existing.l10n_latam_use_documents = True
                return existing
            vals = {'name': name, 'code': code, 'type': jtype,
                    'company_id': company.id, 'default_account_id': account.id}
            if use_docs:
                vals['l10n_latam_use_documents'] = True
            return Journal.create(vals)

        return {
            'sale_journal': journal('sale', 'DSALE', 'Demo Ventas PLE', income),
            'purchase_journal': journal(
                'purchase', 'DPURC', 'Demo Compras PLE', expense),
        }

    def _doc_types(self, pe):
        """Resolve (or create) the PE document types the demo needs.  Works with
        or without l10n_pe installed: existing types are reused, missing ones are
        created (same approach as the module's tests)."""
        DocType = self.env['l10n_latam.document.type'].sudo()

        def resolve(code, name, prefix, must_create=False):
            if not must_create:
                found = DocType.search(
                    [('code', '=', code), ('country_id', '=', pe.id)], limit=1)
                if found:
                    return found[0]
            vals = {'name': name, 'code': code, 'country_id': pe.id}
            if prefix:
                vals['doc_code_prefix'] = prefix
            return DocType.create(vals)

        return {
            'factura': resolve('01', 'Factura', 'F'),
            'nota_credito': resolve('07', 'Nota de Crédito', 'FC'),
            'guia': resolve('09', 'Guía de Remisión Remitente', 'T'),
            # A type WITHOUT a series prefix: posting yields the 'False <num>'
            # placeholder the capture must discard.  Always freshly created so it
            # is guaranteed prefix-less even if l10n_pe seeded a code-01 type.
            'noprefix': resolve('01', 'Factura (sin serie)', None, must_create=True),
        }

    # -- purchase flow -------------------------------------------------------
    def _run_purchase(self, ctx, spec):
        po = self._make_po(ctx, spec['v'], spec['lines'])
        if not po:
            return False
        date = self._date(spec['d'])
        self._validate_picking(po.picking_ids, date)
        moves = po.picking_ids.move_ids
        mode = spec['mode']

        if mode == 'legacy':
            # No bill: the move stays empty; stash the legacy value on the picking
            # so "Recover serie/number stored on the picking" has something to do.
            t = ctx['types']['factura']
            for pk in po.picking_ids:
                pk.sudo().write({
                    'transfer_document_type_id': t.id,
                    'serie_transfer_document': spec['n'].split('-')[0],
                    'number_transfer_document': spec['n'].split('-')[-1],
                })
            return True

        doc_type = ctx['types'][spec['type']]
        post = mode != 'draft_bill'
        bill = self._make_bill(ctx, po, spec['n'], doc_type, post, date)

        if mode == 'empty_derivable':
            moves._itde_clear_auto()          # empty, but the posted bill backs it
        elif mode == 'stale':
            moves.with_context(auto_populate=True).write(
                {'number_transfer_document': 'PENDIENTE'})  # non-manual, wrong
        elif mode == 'manual':
            # Hand-edit with a DIFFERENT number: protected from Re-derive unless
            # the user ticks "Also overwrite manual edits".
            moves.write({
                'transfer_document_type_id': doc_type.id,
                'serie_transfer_document': 'F999',
                'number_transfer_document': '00000001',
            })
        return True

    # -- sale flow -----------------------------------------------------------
    def _run_sale(self, ctx, spec):
        so = self._make_so(ctx, spec['c'], spec['lines'])
        if not so:
            return False
        date = self._date(spec['d'])
        self._validate_picking(so.picking_ids, date)
        moves = so.picking_ids.move_ids
        doc_type = ctx['types'][spec['type']]
        invoice = self._make_invoice(ctx, so, spec['n'], doc_type, date)
        mode = spec['mode']
        if mode == 'empty_derivable':
            moves._itde_clear_auto()
        elif mode == 'stale':
            moves.with_context(auto_populate=True).write(
                {'number_transfer_document': 'PENDIENTE'})
        elif mode == 'manual':
            moves.write({
                'transfer_document_type_id': doc_type.id,
                'serie_transfer_document': 'F999',
                'number_transfer_document': '00000009',
            })
        return True

    # -- internal transfer ---------------------------------------------------
    def _run_internal(self, ctx, spec):
        wh = ctx['warehouse']
        picking = self.env['stock.picking'].create({
            'picking_type_id': wh.int_type_id.id,
            'location_id': wh.lot_stock_id.id,
            'location_dest_id': wh.lot_stock_id.id,
            'origin': 'DEMO Transferencia interna',
        })
        for code, qty in spec['lines']:
            product = self._product(code)
            self.env['stock.move'].create({
                'product_id': product.id,
                'product_uom': product.uom_id.id,
                'product_uom_qty': qty,
                'location_id': wh.lot_stock_id.id,
                'location_dest_id': wh.lot_stock_id.id,
                'picking_id': picking.id,
                'picking_type_id': wh.int_type_id.id,
            })
        self._validate_picking(picking, self._date(spec['d']))
        return True

    # -- purchase return -----------------------------------------------------
    def _run_purchase_return(self, ctx):
        """Receipt + posted Factura, then a vendor return.  The return move
        references the ORIGINAL purchase document (Factura): in Odoo 19 the
        return move carries ``purchase_line_id``, so the capture derives the
        in_invoice on that line.  (The module's separate credit-note branch --
        via origin_returned_move_id -- only triggers when the return move has no
        purchase line, which is not the case here.)"""
        po = self._make_po(ctx, 'vendor_tecnoandes', [('monitor', 4, 620.0)])
        if not po:
            return False
        self._validate_picking(po.picking_ids, self._date('02-28'))
        receipt = po.picking_ids.filtered(lambda p: p.state == 'done')[:1]
        if not receipt:
            return False
        # Post the vendor bill first so the return, once validated, captures the
        # original Factura through its purchase line.
        self._make_bill(ctx, po, 'F001-00004600', ctx['types']['factura'],
                        True, self._date('02-28'))
        self._return_picking(receipt, self._date('03-10'))
        return True

    # -- builders ------------------------------------------------------------
    def _make_po(self, ctx, vendor_key, lines):
        vendor = self._partner(vendor_key)
        po = self.env['purchase.order'].create({
            'partner_id': vendor.id,
            'order_line': [(0, 0, {
                'product_id': self._product(code).id,
                'product_qty': qty,
                'price_unit': price,
            }) for code, qty, price in lines],
        })
        po.button_confirm()
        return po

    def _make_bill(self, ctx, po, number, doc_type, post, date):
        bill = self.env['account.move'].sudo().create({
            'move_type': 'in_invoice',
            'partner_id': po.partner_id.id,
            'invoice_date': date.date(),
            'journal_id': ctx['purchase_journal'].id,
            'invoice_line_ids': [(0, 0, {
                'product_id': line.product_id.id,
                'quantity': line.product_qty,
                'price_unit': line.price_unit,
                'purchase_line_id': line.id,
            }) for line in po.order_line],
        })
        bill.write({
            'l10n_latam_document_type_id': doc_type.id,
            'l10n_latam_manual_document_number': True,
            'l10n_latam_document_number': number,
        })
        if post:
            bill.action_post()
        return bill

    def _make_so(self, ctx, customer_key, lines):
        customer = self._partner(customer_key)
        so = self.env['sale.order'].create({
            'partner_id': customer.id,
            'order_line': [(0, 0, {
                'product_id': self._product(code).id,
                'product_uom_qty': qty,
                'price_unit': price,
            }) for code, qty, price in lines],
        })
        so.action_confirm()
        return so

    def _make_invoice(self, ctx, so, number, doc_type, date):
        invoice = so._create_invoices()
        invoice.journal_id = ctx['sale_journal'].id
        invoice.write({
            'invoice_date': date.date(),
            'l10n_latam_document_type_id': doc_type.id,
            'l10n_latam_manual_document_number': True,
            'l10n_latam_document_number': number,
        })
        invoice.action_post()
        return invoice

    def _return_picking(self, picking, date):
        wizard = self.env['stock.return.picking'].with_context(
            active_id=picking.id, active_ids=picking.ids,
            active_model='stock.picking').create({})
        for line in wizard.product_return_moves:
            line.quantity = line.quantity or line.move_id.product_uom_qty
        action = wizard.action_create_returns()
        ret = self.env['stock.picking'].browse(action['res_id'])
        self._validate_picking(ret, date)
        return ret

    # -- validation / back-dating -------------------------------------------
    def _validate_picking(self, pickings, date):
        for picking in pickings:
            picking.action_assign()
            for ml in picking.move_line_ids:
                ml.quantity = ml.move_id.product_uom_qty
                ml.picked = True
            res = picking.button_validate()
            if isinstance(res, dict) and res.get('res_model'):
                wiz = self.env[res['res_model']].with_context(
                    res.get('context', {})).create({})
                if hasattr(wiz, 'process'):
                    wiz.process()
            self._backdate(picking, date)

    def _backdate(self, picking, date):
        picking.move_ids.write({'date': date})
        picking.write({'date_done': date, 'scheduled_date': date})

    # -- helpers -------------------------------------------------------------
    def _date(self, day):
        month, dom = (int(x) for x in day.split('-'))
        return datetime(_YEAR, month, dom, 10, 0, 0)

    def _product(self, code):
        return self.env.ref('invoice_type_document_extension.product_%s' % code)

    def _partner(self, key):
        return self.env.ref('invoice_type_document_extension.%s' % key)
