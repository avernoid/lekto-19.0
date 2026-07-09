from odoo.fields import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestWorkOrderReport(TransactionCase):
    """Behavioural tests for the Work Order PDF report.

    The whole module's logic lives in the QWeb template
    (``custom_work_order.report_work_order``): the OT number, the total
    weight, the source-location branching, the line ``extra_desc`` and the
    shipping fallback are all Python expressions evaluated at render time.
    A bare install/smoke test never executes them, so every test here
    RENDERS THE REAL REPORT and asserts on the produced output — the only
    way to protect this module from a broken ``t-out`` reaching production.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # --- Storable good with a known weight (drives Part 1 + total) ----
        cls.product = cls.env["product.product"].create({
            "name": "Steel Beam ZX",
            "type": "consu",
            "is_storable": True,
            "weight": 2.5,
            "list_price": 100.0,
            "invoice_policy": "order",
        })

        # --- Customer (commercial entity) + dedicated delivery address ----
        cls.customer = cls.env["res.partner"].create({
            "name": "ACME Corp ZZ",
            "is_company": True,
            "vat": "RUC20999888",
        })
        cls.delivery = cls.env["res.partner"].create({
            "name": "ACME Warehouse",
            "parent_id": cls.customer.id,
            "type": "delivery",
            "street": "Av. Industrial 100",
            "street2": "Gate 3 - Dock B",
            "phone": "+51 999 111 222",
            "delivery_contact_name": "John Receiver",
            "comment": "Ring the bell twice",
        })

        # --- Sales order feeding every report field; confirm -> picking ---
        cls.sale = cls.env["sale.order"].create({
            "partner_id": cls.customer.id,
            "partner_shipping_id": cls.delivery.id,
            "client_order_ref": "PROJECT-ALPHA-77",
            "customer_purchase_order": "OC-55512",
            "work_order_observations": "Handle with extreme care ZZ",
            "order_line": [Command.create({
                "product_id": cls.product.id,
                "product_uom_qty": 3.0,
                "name": "Steel Beam ZX\nExtra spec line ZZ",
            })],
        })
        cls.sale.action_confirm()
        cls.picking = cls.sale.picking_ids[:1]

        cls.report = cls.env.ref("custom_work_order.report_work_order_action")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _render_html(self, pickings):
        """Render the report to HTML (no wkhtmltopdf needed) as a string."""
        html = self.env["ir.actions.report"]._render_qweb_html(
            "custom_work_order.report_work_order", pickings.ids,
        )[0]
        if isinstance(html, bytes):
            html = html.decode("utf-8")
        return html

    # ------------------------------------------------------------------
    # 1. Structural / registration
    # ------------------------------------------------------------------

    def test_delivery_contact_field_exists(self):
        """The single new field must exist on res.partner as a Char."""
        field = self.env["res.partner"]._fields.get("delivery_contact_name")
        self.assertIsNotNone(field, "delivery_contact_name missing on res.partner")
        self.assertEqual(field.type, "char")

    def test_report_action_registered_and_bound(self):
        """Report must be a qweb-pdf bound to stock.picking."""
        self.assertEqual(self.report.model, "stock.picking")
        self.assertEqual(self.report.report_type, "qweb-pdf")
        self.assertEqual(self.report.binding_model_id.model, "stock.picking")

    def test_picking_was_created(self):
        """Pre-condition: confirming the SO produced a delivery picking."""
        self.assertTrue(self.picking, "No picking created from the sales order")

    # ------------------------------------------------------------------
    # 2. The report actually renders (the #1 regression guard)
    # ------------------------------------------------------------------

    def test_pdf_renders_without_error(self):
        """The PDF pipeline must produce content for a normal picking.

        wkhtmltopdf may be absent in CI, in which case Odoo transparently
        falls back to HTML; either way the render must succeed and return a
        non-empty document (this guards the whole QWeb-to-PDF path).
        """
        content, content_type = self.report._render_qweb_pdf(
            self.report.report_name, self.picking.ids,
        )
        self.assertIn(content_type, ("pdf", "html"))
        self.assertTrue(content, "Work Order document was not generated")

    def test_html_has_three_parts(self):
        """The three sections must all be present."""
        html = self._render_html(self.picking)
        self.assertIn("PARTE 1", html)
        self.assertIn("PARTE 2", html)
        self.assertIn("PARTE 3", html)
        self.assertIn("ORDEN DE TRABAJO", html)

    # ------------------------------------------------------------------
    # 3. Business rules computed in the template
    # ------------------------------------------------------------------

    def test_work_order_number_combines_sale_and_picking(self):
        """OT number = '<sale>-<picking>' when the picking has a sale order."""
        html = self._render_html(self.picking)
        self.assertIn(f"{self.sale.name}-{self.picking.name}", html)

    def test_total_weight_sums_line_weights(self):
        """Total weight = product weight * qty, summed over moves (2.5 * 3)."""
        html = self._render_html(self.picking)
        self.assertIn("Peso total OT", html)
        self.assertIn("7.50", html)

    def test_extra_description_strips_product_name(self):
        """extra_desc = sale line name minus the product display name."""
        html = self._render_html(self.picking)
        # The bold product name shows once...
        self.assertIn("Steel Beam ZX", html)
        # ...and the residual line note is rendered as extra description.
        self.assertIn("Extra spec line ZZ", html)

    def test_location_pending_when_not_reserved(self):
        """No reservation and no MTO origin -> source location is 'Pendiente'."""
        # Nothing was put in stock, so the move cannot reserve anything.
        html = self._render_html(self.picking)
        self.assertIn("Pendiente", html)

    def test_location_shows_real_location_when_reserved(self):
        """Reserved stock -> the move line's source location is printed."""
        self.env["stock.quant"]._update_available_quantity(
            self.product, self.picking.location_id, 10.0,
        )
        self.picking.action_assign()
        move_line = self.picking.move_ids.move_line_ids[:1]
        self.assertTrue(move_line, "Stock was not reserved; test pre-condition failed")
        loc_name = move_line.location_id.complete_name
        html = self._render_html(self.picking)
        self.assertIn(loc_name, html)
        # The reserved row must no longer fall back to the 'Pendiente' label.
        self.assertNotIn("Pendiente", html)

    def test_cancelled_move_excluded_from_products_and_weight(self):
        """Cancelled moves must not appear nor count toward the total weight."""
        product_b = self.env["product.product"].create({
            "name": "Copper Wire QQ",
            "type": "consu",
            "is_storable": True,
            "weight": 1.0,
        })
        sale2 = self.env["sale.order"].create({
            "partner_id": self.customer.id,
            "partner_shipping_id": self.delivery.id,
            "order_line": [
                Command.create({"product_id": self.product.id, "product_uom_qty": 3.0}),
                Command.create({"product_id": product_b.id, "product_uom_qty": 5.0}),
            ],
        })
        sale2.action_confirm()
        picking2 = sale2.picking_ids[:1]
        move_b = picking2.move_ids.filtered(lambda m: m.product_id == product_b)
        move_b._action_cancel()

        html = self._render_html(picking2)
        self.assertNotIn("Copper Wire QQ", html, "Cancelled product still printed")
        # Only Steel Beam ZX (2.5 * 3 = 7.50) counts; the 5 kg of copper is excluded.
        self.assertIn("7.50", html)

    # ------------------------------------------------------------------
    # 4. Values pulled from related records
    # ------------------------------------------------------------------

    def test_customer_oc_and_project_are_printed(self):
        """Customer, RUC, OC (customer_purchase_order) and project are shown."""
        html = self._render_html(self.picking)
        self.assertIn("ACME Corp ZZ", html)
        self.assertIn("RUC20999888", html)
        self.assertIn("OC-55512", html)
        self.assertIn("PROJECT-ALPHA-77", html)

    def test_observations_from_sale_order(self):
        """Part 2 prints the sale order's work_order_observations text."""
        html = self._render_html(self.picking)
        self.assertIn("Handle with extreme care ZZ", html)

    def test_shipping_details_use_delivery_address(self):
        """Part 3 prints address, the new delivery contact, phone and notes."""
        html = self._render_html(self.picking)
        self.assertIn("Av. Industrial 100", html)
        self.assertIn("Gate 3 - Dock B", html)
        self.assertIn("John Receiver", html)
        self.assertIn("+51 999 111 222", html)
        self.assertIn("Ring the bell twice", html)

    # ------------------------------------------------------------------
    # 5. Data-dependent branch: picking WITHOUT a sales order
    # ------------------------------------------------------------------

    def test_renders_for_picking_without_sale_order(self):
        """A picking with no sale order must still render; OT number = picking name."""
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1,
        )
        picking = self.env["stock.picking"].create({
            "picking_type_id": warehouse.out_type_id.id,
            "partner_id": self.customer.id,
            "location_id": warehouse.lot_stock_id.id,
            "location_dest_id": self.env.ref("stock.stock_location_customers").id,
        })
        self.assertFalse(picking.sale_id, "Test pre-condition: picking must have no sale")
        html = self._render_html(picking)
        self.assertIn(picking.name, html)
        # Sales-only fields degrade gracefully to '-'.
        self.assertIn("ORDEN DE TRABAJO", html)
