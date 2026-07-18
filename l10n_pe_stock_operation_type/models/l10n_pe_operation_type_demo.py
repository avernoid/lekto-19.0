import logging
from datetime import datetime

from odoo import api, models

from .stock_move import L10N_PE_OPERATION_TYPE_SELECTION

_logger = logging.getLogger(__name__)

# Year every demo movement is back-dated into. Spread Jan-Jun so any period the
# presenter picks shows real movements (today in the demo timeline is Jul).
_YEAR = 2026

# Marker so the whole generation runs at most once (the demo <function> would
# otherwise re-run on every module update and duplicate everything).
_DEMO_FLAG = "l10n_pe_stock_operation_type.demo_generated"

# Human label per SUNAT Table-12 code, for logging and the catalogue sweep.
_LABELS = dict(L10N_PE_OPERATION_TYPE_SELECTION)

# ---------------------------------------------------------------------------
# Scenario tables.  Each row is (origin_label_es, kind, code, count):
#   kind    : how the physical move is built --
#             'in'        supplier   -> stock     (incoming)
#             'out'       stock      -> customer   (outgoing)
#             'internal'  stock      -> secondary  (internal transfer)
#             'inv_out'   stock      -> inventory  (adjustment / loss)  [no picking]
#             'inv_in'    inventory  -> stock      (adjustment / gain)  [no picking]
#             'scrap'     stock.scrap                                    [no picking]
#   code    : 'auto'  -> keep the code the engine inferred on validation
#             'empty' -> clear the code after validation (for the live wizard)
#             '<nn>'  -> overwrite by hand to that Table-12 code (stamps manual)
#   count   : how many moves to create -- kept generous so every use case shows
#             many rows in a live list, grouped by the Operation Type column.
# ---------------------------------------------------------------------------

# A) Heuristic autocompletion: the codes the engine infers by itself on _action_done.
#    These land with the manual flag OFF (provenance = automatic).
_AUTO_SCENARIOS = [
    ("Compras nacionales (auto 02)",            "in",       "auto", 16),
    ("Ventas nacionales (auto 01)",             "out",      "auto", 16),
    ("Transferencias internas (auto 21)",       "internal", "auto", 10),
    ("Ajuste inventario - faltante (auto 28)",  "inv_out",  "auto", 8),
    ("Ajuste inventario - sobrante (auto 28)",  "inv_in",   "auto", 6),
    ("Desmedro / mermas (auto 13)",             "scrap",    "auto", 8),
]

# B) Manual classification: the accountant reclassifies to a specific Table-12
#    code the heuristic cannot know.  Written by hand -> provenance = manual, so
#    a later auto pass never clobbers them.  Many rows per code on purpose.
_MANUAL_SCENARIOS = [
    ("Consignacion recibida (03)",              "in",       "3",  6),
    ("Consignacion entregada (04)",             "out",      "4",  6),
    ("Devolucion recibida del cliente (05)",    "in",       "5",  6),
    ("Devolucion entregada al proveedor (06)",  "out",      "6",  6),
    ("Bonificacion (07)",                       "out",      "7",  6),
    ("Premio (08)",                             "out",      "8",  5),
    ("Donacion (09)",                           "out",      "9",  6),
    ("Salida a produccion (10)",                "out",      "10", 6),
    ("Retiro (12)",                             "out",      "12", 5),
    ("Deterioro (14)",                          "out",      "14", 5),
    ("Destruccion (15)",                        "out",      "15", 5),
    ("Exportacion (17)",                        "out",      "17", 8),
    ("Importacion (18)",                        "in",       "18", 8),
    ("Ingreso de produccion (19)",              "in",       "19", 6),
    ("Devolucion de produccion (20)",           "in",       "20", 5),
    ("Ingreso por confusion (22)",              "in",       "22", 4),
    ("Salida por confusion (23)",               "out",      "23", 4),
    ("Ingreso por devolucion de cliente (24)",  "in",       "24", 5),
    ("Devolucion a proveedor (25)",             "out",      "25", 5),
    ("Ingreso por servicio de produccion (26)", "in",       "26", 4),
    ("Salida por servicio de produccion (27)",  "out",      "27", 5),
    ("Ingreso de bienes en prestamo (29)",      "in",       "29", 4),
    ("Salida de bienes en prestamo (30)",       "out",      "30", 4),
    ("Ingreso de bienes en custodia (31)",      "in",       "31", 4),
    ("Salida de bienes en custodia (32)",       "out",      "32", 4),
    ("Publicidad (34)",                         "out",      "34", 4),
    ("Gastos de representacion (35)",           "out",      "35", 4),
]

# C) Catalogue sweep: every remaining Table-12 code gets at least a couple of
#    moves so the whole legal catalogue is represented at least once.  Direction
#    is a plausible default per code.
_SWEEP = [
    ("Traslado entre almacenes (11)",           "internal", "11", 3),
    ("Muestras medicas (33)",                   "out",      "33", 2),
    ("Retiro entrega a trabajadores (36)",      "out",      "36", 2),
    ("Retiro por convenio colectivo (37)",      "out",      "37", 2),
    ("Retiro por reposicion de danados (38)",   "out",      "38", 2),
    ("Otros 1 (91)",                            "in",       "91", 2),
    ("Otros 2 (92)",                            "out",      "92", 2),
    ("Otros 3 (93)",                            "in",       "93", 2),
    ("Otros 4 (94)",                            "out",      "94", 2),
    ("Otros 5 (95)",                            "in",       "95", 2),
    ("Otros 6 (96)",                            "out",      "96", 2),
    ("Otros 7 (97)",                            "in",       "97", 2),
    ("Otros 8 (98)",                            "out",      "98", 2),
    ("Otros (99)",                              "in",       "99", 2),
]


class L10nPeOperationTypeDemo(models.AbstractModel):
    """Programmatic generator for the SUNAT operation-type demo.

    The operation type is inferred on ``_action_done`` and only for a Peruvian
    company, so the demo moves must go through the real confirm/assign/done flow
    (that cannot be expressed as flat XML records forced to ``state=done``).
    Invoked once from ``demo/l10n_pe_stock_operation_type_demo.xml`` via a
    ``<function>`` tag; idempotent through an ``ir.config_parameter`` flag.
    """

    _name = "l10n_pe.operation.type.demo"
    _description = "SUNAT operation-type demo data generator"

    # -- entry point (called from the demo XML) ------------------------------
    @api.model
    def _generate_demo_data(self):
        icp = self.env["ir.config_parameter"].sudo()
        if icp.get_param(_DEMO_FLAG):
            return  # already generated on a previous install/update

        # The heuristic only fires for a Peruvian company (country_code == 'PE').
        # Prefer an existing PE company (the one l10n_pe's own demo creates, which
        # is the company a presenter actually opens) so the moves land where they
        # are looked at; only if none exists fall back to the main company and
        # force it to PE. Never create a second, confusing PE company.
        pe = self.env.ref("base.pe", raise_if_not_found=False)
        # Prefer an existing PE company (the one l10n_pe's own demo creates, which
        # is the company a presenter actually opens) so the moves land where they
        # are looked at. res.company.country_id is not stored (not searchable), so
        # go through the company partner's country, which is stored.
        company = self.env["res.company"].search(
            [("partner_id.country_id", "=", pe.id)], limit=1) if pe else False
        if not company:
            # No PE company yet: fall back to the main one and force it to PE.
            company = self.env.ref("base.main_company", raise_if_not_found=False)
            if not company:
                return
            if pe and company.country_id != pe:
                company.sudo().country_id = pe

        # Guarantee a warehouse in that company (a demo-created PE company may not
        # have one), so the demo is self-contained wherever it lands.
        Warehouse = self.env["stock.warehouse"]
        warehouse = Warehouse.search([("company_id", "=", company.id)], limit=1)
        if not warehouse:
            warehouse = Warehouse.sudo().with_company(company).create({
                "name": "Almacen Demo SUNAT",
                "code": "DMO",
            })

        gen = self.sudo().with_company(company).with_context(
            allowed_company_ids=[company.id])
        env = gen.env

        secondary = env["stock.location"].create({
            "name": "Almacen Secundario (Demo SUNAT)",
            "usage": "internal",
            "location_id": warehouse.lot_stock_id.location_id.id,
        })
        inventory_loc = env["stock.location"].create({
            "name": "Ajuste de Inventario (Demo SUNAT)",
            "usage": "inventory",
        })
        ctx = {
            "company": company,
            "warehouse": warehouse,
            "stock": warehouse.lot_stock_id,
            "secondary": secondary,
            "inventory": inventory_loc,
            "supplier": env.ref("stock.stock_location_suppliers"),
            "customer": env.ref("stock.stock_location_customers"),
            "vendor": env.ref("l10n_pe_stock_operation_type.partner_op_vendor"),
            "client": env.ref("l10n_pe_stock_operation_type.partner_op_customer"),
        }

        products = [
            env.ref("l10n_pe_stock_operation_type.product_op_%02d" % n)
            for n in range(1, 7)
        ]
        products = [p.with_company(company) for p in products]
        # Running counters -> product round-robin + a spread of back-dates.
        state = {"i": 0}

        # 0) Opening balance: a big receipt per product (code 16, manual). This
        #    seeds stock so every later out/internal/scrap has something to move,
        #    and demonstrates the Opening Balance use case at the same time.
        for product in products:
            gen._demo_picking_batch(
                ctx, state, [product], "Saldo inicial (16)",
                "in", "16", 1, qty=3000)

        # A) Heuristic autocompletion (provenance = automatic).
        for label, kind, code, count in _AUTO_SCENARIOS:
            gen._demo_run(ctx, state, products, label, kind, code, count)

        # B) Manual reclassification (provenance = manual).
        for label, kind, code, count in _MANUAL_SCENARIOS:
            gen._demo_run(ctx, state, products, label, kind, code, count)

        # C) Catalogue sweep (every remaining Table-12 code at least once).
        for label, kind, code, count in _SWEEP:
            gen._demo_run(ctx, state, products, label, kind, code, count)

        # D) Wizard playground: one clearly labelled set mixing empty / auto /
        #    manual moves so the presenter can open the mass-assignment wizard
        #    live and watch the policy filters (only-empty / overwrite-auto /
        #    overwrite-all) and the live preview count change.
        gen._demo_wizard_playground(ctx, state, products)

        icp.set_param(_DEMO_FLAG, "1")
        _logger.info(
            "l10n_pe operation-type demo: generated %s moves across %s use cases.",
            state["i"], len(_AUTO_SCENARIOS) + len(_MANUAL_SCENARIOS)
            + len(_SWEEP) + 1)

    # -- scenario dispatch ---------------------------------------------------
    def _demo_run(self, ctx, state, products, label, kind, code, count):
        if kind == "scrap":
            for _n in range(count):
                self._demo_scrap(ctx, state, products, label)
        elif kind in ("inv_out", "inv_in"):
            for _n in range(count):
                self._demo_inventory_move(ctx, state, products, label, kind, code)
        else:
            # Group the batch under a single transfer -> reads as one realistic
            # picking with many lines, while each line is its own Kardex row.
            self._demo_picking_batch(ctx, state, products, label, kind, code, count)

    # -- picking-based batch (in / out / internal) ---------------------------
    def _demo_picking_batch(self, ctx, state, products, label, kind, code,
                            count, qty=None):
        picking_type, src, dst, partner = self._demo_route(ctx, kind)
        picking = self.env["stock.picking"].create({
            "picking_type_id": picking_type.id,
            "location_id": src.id,
            "location_dest_id": dst.id,
            "partner_id": partner.id if partner else False,
            "origin": "DEMO SUNAT · %s" % label,
        })
        moves, dates = self.env["stock.move"], []
        for _n in range(count):
            product = products[state["i"] % len(products)]
            move_qty = qty if qty is not None else 10 + (state["i"] % 5) * 5
            date = self._demo_date(state["i"])
            move = self.env["stock.move"].create({
                "product_id": product.id,
                "product_uom": product.uom_id.id,
                "product_uom_qty": move_qty,
                "location_id": src.id,
                "location_dest_id": dst.id,
                "picking_id": picking.id,
                "picking_type_id": picking_type.id,
            })
            moves |= move
            dates.append(date)
            state["i"] += 1
        # Validate the whole transfer ONCE so _action_done fires for every line
        # together and the heuristic classifies them all (not just the first).
        self._demo_validate_picking(picking, moves)
        for move, date in zip(moves, dates):
            move.write({"date": date})
        picking.write({"date_done": dates[-1], "scheduled_date": dates[-1]})
        self._demo_classify(moves, code, ctx)
        return moves

    def _demo_validate_picking(self, picking, moves):
        """Confirm/assign/pick and validate a whole transfer in one shot.

        Confirm with ``merge=False``: Odoo would otherwise merge same-product
        lines into a single move, leaving our recordset pointing at deleted ids.
        Validating the whole set with one ``_action_done`` fires the heuristic
        for every line together, so the auto scenarios get many rows, not one.
        """
        moves._action_confirm(merge=False)
        moves._action_assign()
        for move in moves:
            move.quantity = move.product_uom_qty
            move.picked = True
        moves._action_done()

    # -- bare inventory-adjustment move (usage='inventory' -> code 28) --------
    def _demo_inventory_move(self, ctx, state, products, label, kind, code):
        product = products[state["i"] % len(products)]
        qty = 3 + (state["i"] % 4)
        date = self._demo_date(state["i"])
        src = ctx["inventory"] if kind == "inv_in" else ctx["stock"]
        dst = ctx["stock"] if kind == "inv_in" else ctx["inventory"]
        move = self.env["stock.move"].create({
            "product_id": product.id,
            "product_uom": product.uom_id.id,
            "product_uom_qty": qty,
            "location_id": src.id,
            "location_dest_id": dst.id,
            "origin": "DEMO SUNAT · %s" % label,
        })
        self._demo_validate(move, qty)
        move.write({"date": date})
        state["i"] += 1
        self._demo_classify(move, code, ctx)
        return move

    # -- scrap move (scrap_id set -> code 13) --------------------------------
    def _demo_scrap(self, ctx, state, products, label):
        product = products[state["i"] % len(products)]
        qty = 1 + (state["i"] % 3)
        date = self._demo_date(state["i"])
        scrap = self.env["stock.scrap"].create({
            "product_id": product.id,
            "product_uom_id": product.uom_id.id,
            "scrap_qty": qty,
            "location_id": ctx["stock"].id,
            "origin": "DEMO SUNAT · %s" % label,
        })
        scrap.do_scrap()
        move = scrap.move_ids[:1]
        if move:
            move.write({"date": date})
        state["i"] += 1
        # 'auto' only: validation already inferred 13; nothing to overwrite.
        return move

    # -- the live wizard demo set --------------------------------------------
    def _demo_wizard_playground(self, ctx, state, products):
        # Incoming batch left with NO type, on its own transfer, so from_picking
        # has a native picking type to copy down when the PLE reports module is
        # present.  Split the moves into empty / auto / manual thirds.
        picking_type, src, dst, partner = self._demo_route(ctx, "in")
        picking = self.env["stock.picking"].create({
            "picking_type_id": picking_type.id,
            "location_id": src.id,
            "location_dest_id": dst.id,
            "partner_id": partner.id,
            "origin": "DEMO SUNAT · Wizard en vivo (selecciona y usa la accion)",
        })
        if "l10n_pe_operation_type" in self.env["stock.picking"]._fields:
            # So the wizard 'From the transfer (picking)' source has data to copy.
            picking.l10n_pe_operation_type = "18"  # Import
        empty, auto, manual = self.env["stock.move"], self.env["stock.move"], \
            self.env["stock.move"]
        moves, dates = self.env["stock.move"], []
        for n in range(30):
            product = products[state["i"] % len(products)]
            qty = 8 + (state["i"] % 4) * 4
            date = self._demo_date(state["i"])
            move = self.env["stock.move"].create({
                "product_id": product.id,
                "product_uom": product.uom_id.id,
                "product_uom_qty": qty,
                "location_id": src.id,
                "location_dest_id": dst.id,
                "picking_id": picking.id,
                "picking_type_id": picking_type.id,
            })
            moves |= move
            dates.append(date)
            state["i"] += 1
            if n % 3 == 0:
                empty |= move
            elif n % 3 == 1:
                auto |= move
            else:
                manual |= move
        # Validate the whole transfer once so every line gets the auto code.
        self._demo_validate_picking(picking, moves)
        for move, date in zip(moves, dates):
            move.write({"date": date})
        picking.write({"date_done": dates[-1], "scheduled_date": dates[-1]})
        self._demo_classify(empty, "empty", ctx)     # left blank for the wizard
        # auto: keep the inferred '02' (provenance auto) -> overwrite-auto hits it
        self._demo_classify(manual, "7", ctx)         # Bonus, by hand -> protected

    # -- helpers -------------------------------------------------------------
    def _demo_route(self, ctx, kind):
        """(picking_type, src, dst, partner) for a picking-based ``kind``."""
        wh = ctx["warehouse"]
        if kind == "in":
            return wh.in_type_id, ctx["supplier"], ctx["stock"], ctx["vendor"]
        if kind == "out":
            return wh.out_type_id, ctx["stock"], ctx["customer"], ctx["client"]
        # internal
        return wh.int_type_id, ctx["stock"], ctx["secondary"], None

    def _demo_validate(self, move, qty):
        """Confirm/assign/pick/validate one move through the real flow so the
        engine computes state, is_in/is_out and fires the auto inference."""
        move._action_confirm()
        move._action_assign()
        move.quantity = qty
        move.picked = True
        move._action_done()

    def _demo_classify(self, moves, code, ctx):
        """Apply the intended provenance to already-done moves.

        'auto'  -> nothing (validation already inferred the code, flag OFF).
        'empty' -> clear the code with the auto context, flag OFF (for wizard).
        '<nn>'  -> overwrite by hand: the write() gate stamps the manual flag.
        """
        moves = moves.filtered(lambda m: m.company_id.country_code == "PE")
        if not moves or code == "auto":
            return
        if code == "empty":
            moves.with_context(l10n_pe_op_auto=True).write({
                "l10n_pe_operation_type": False,
                "l10n_pe_operation_type_manual": False,
            })
        else:
            moves.write({"l10n_pe_operation_type": code})

    def _demo_date(self, i):
        """A spread of back-dates across Jan-Jun so any period is populated."""
        month = 1 + (i % 6)
        day = 1 + (i * 5) % 27
        return datetime(_YEAR, month, day, 12, 0, 0)
