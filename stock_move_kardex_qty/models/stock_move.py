from odoo import api, fields, models


class StockMove(models.Model):
    """Quantity-only Kardex column at the movement level.

    ``kardex_qty`` is the signed valued quantity of the move: it is the natural
    entry-level ledger because quantity telescopes trivially -- Sum(in - out)
    reconciles with the on-hand valued quantity with no cost replay at all,
    which is exactly the hard part the *valued* Kardex has to solve.  Nobody
    else reads these fields; they only feed reporting views.
    """

    _inherit = "stock.move"

    kardex_qty = fields.Float(
        string="Kardex Qty",
        compute="_compute_kardex_qty",
        store=True,
        digits="Product Unit of Measure",
        aggregator="sum",
        help="Signed valued quantity for a stock ledger (Kardex): the valued "
             "quantity as +incoming / -outgoing, and 0 for anything that is "
             "neither (internal transfers, dropship, non-done moves). Expressed "
             "in the product's reference Unit of Measure -- see 'Kardex UoM', "
             "NOT the operational move UoM. Subtotals are meaningful only "
             "within a single product (or a UoM-homogeneous group).",
    )
    kardex_uom_id = fields.Many2one(
        "uom.uom",
        string="Kardex UoM",
        related="product_id.uom_id",
        store=True,
        readonly=True,
        aggregator=False,
        help="Reference Unit of Measure of the Kardex quantity: the product's "
             "own UoM, in which the valued quantity is expressed (NOT the "
             "operational move UoM). Shown next to 'Kardex Qty' so a mixed-UoM "
             "subtotal is visibly meaningless instead of a clean but wrong "
             "number.",
    )

    @api.depends(
        "state",
        "is_in",
        "is_out",
        "move_line_ids.quantity_product_uom",
        "move_line_ids.picked",
        "move_line_ids.owner_id",
        "product_id.uom_id",
    )
    def _compute_kardex_qty(self):
        for move in self:
            if move.state != "done":
                move.kardex_qty = 0.0
            elif move.is_in:
                move.kardex_qty = move._get_valued_qty()
            elif move.is_out:
                move.kardex_qty = -move._get_valued_qty()
            else:
                # Internal transfers, dropship and anything not valued as a pure
                # in/out contribute 0 -- they do not change on-hand quantity, so
                # excluding them keeps Sum(kardex_qty) reconciled with on-hand.
                move.kardex_qty = 0.0

    # ------------------------------------------------------------------
    # Demo data (loaded from demo/kardex_qty_demo.xml). Kept here so the demo
    # moves are built through the real confirm/assign/done flow -- valuation and
    # is_in/is_out are then genuine, unlike moves forced to state=done in XML.
    # ------------------------------------------------------------------
    @api.model
    def _kardex_qty_build_demo(self):
        """Build done moves that exercise every kardex_qty branch.

        Idempotent: skipped once the demo product already has moves (re-runs on
        module update do not duplicate).
        """
        Product = self.env["product.product"]
        product = Product.search([("default_code", "=", "KRDX-DEMO")], limit=1)
        if product and product.stock_move_ids:
            return
        if not product:
            product = Product.create({
                "name": "Kardex Demo Product",
                "default_code": "KRDX-DEMO",
                "type": "consu",
                "is_storable": True,
                "uom_id": self.env.ref("uom.product_uom_unit").id,
            })
        unit = self.env.ref("uom.product_uom_unit")
        dozen = self.env.ref("uom.product_uom_dozen")
        stock = self.env.ref("stock.stock_location_stock")
        suppliers = self.env.ref("stock.stock_location_suppliers")
        customers = self.env.ref("stock.stock_location_customers")
        secondary = self.env["stock.location"].create({
            "name": "Kardex Demo Secondary",
            "usage": "internal",
            "location_id": stock.location_id.id,
        })
        # Order matters: stock the two receipts first so the out / internal moves
        # have something to move.
        self._kardex_qty_demo_move(product, 10, unit, suppliers, stock)    # +10 (in)
        self._kardex_qty_demo_move(product, 2, dozen, suppliers, stock)    # +24 (in, UoM != product UoM: 2 dozen -> 24 units)
        self._kardex_qty_demo_move(product, 3, unit, stock, customers)     # -3  (out)
        self._kardex_qty_demo_move(product, 4, unit, stock, secondary)     # 0   (internal transfer: not valued in/out)
        self._kardex_qty_demo_move(product, 1, unit, customers, stock)     # +1  (customer return -> counts as in)

    @api.model
    def _kardex_qty_demo_move(self, product, qty, uom, src, dst):
        """Create and fully validate one demo move (qty expressed in ``uom``)."""
        move = self.env["stock.move"].create({
            "product_id": product.id,
            "product_uom_qty": qty,
            "product_uom": uom.id,
            "location_id": src.id,
            "location_dest_id": dst.id,
        })
        move._action_confirm()
        move._action_assign()
        for ml in move.move_line_ids:
            ml.quantity = qty
            ml.picked = True
        move._action_done()
        return move
