from lxml import etree

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSaleCustomFields(TransactionCase):
    """Protect the actual contract of sale_custom_fields:

    the three fields persist, the form xpath keeps hooking into the standard
    'order_details' group, the Description column ships hidden-but-optional in
    both list views, and the Spanish translation resolves.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.SaleOrder = cls.env["sale.order"]
        cls.partner = cls.env["res.partner"].create({"name": "ACME Test Customer"})

        # Activate Spanish and load this module's terms so the translation
        # assertion exercises the real i18n/es.po (not just English defaults).
        cls.env["res.lang"]._activate_lang("es_ES")
        cls.env["ir.module.module"].search(
            [("name", "=", "sale_custom_fields")]
        )._update_translations("es_ES")

    def _new_order(self, **vals):
        return self.SaleOrder.create({"partner_id": self.partner.id, **vals})

    # ------------------------------------------------------------------
    # 1. Persistence — guards against the fields being dropped / renamed
    # ------------------------------------------------------------------
    def test_fields_persist_on_create_and_write(self):
        order = self._new_order(
            sale_description="Office furniture - Q3 restock",
            customer_purchase_order="PO-12345",
            work_order_observations="Deliver before 9am to dock B.",
        )
        order.invalidate_recordset()
        self.assertEqual(order.sale_description, "Office furniture - Q3 restock")
        self.assertEqual(order.customer_purchase_order, "PO-12345")
        self.assertEqual(
            order.work_order_observations, "Deliver before 9am to dock B."
        )

        # Round-trip through write as well.
        order.write({"customer_purchase_order": "PO-99999"})
        order.invalidate_recordset()
        self.assertEqual(order.customer_purchase_order, "PO-99999")

    def test_fields_are_informational_only(self):
        """The fields must never interfere with the standard sales flow:
        a blank order still confirms and prices normally."""
        order = self._new_order()
        self.assertFalse(order.sale_description)
        self.assertFalse(order.customer_purchase_order)
        self.assertFalse(order.work_order_observations)
        order.action_confirm()
        self.assertEqual(order.state, "sale")

    # ------------------------------------------------------------------
    # 2. Form view — guards the xpath against //group[@name='order_details']
    #    disappearing/renaming in a future Odoo version.
    # ------------------------------------------------------------------
    def test_form_view_exposes_custom_fields(self):
        arch = self.SaleOrder.get_view(
            self.env.ref("sale.view_order_form").id, "form"
        )["arch"]
        tree = etree.fromstring(arch)
        for field_name in (
            "sale_description",
            "customer_purchase_order",
            "work_order_observations",
        ):
            self.assertTrue(
                tree.xpath("//field[@name='%s']" % field_name),
                "Field %s is not rendered in the sale order form view; the "
                "inherited xpath probably stopped matching." % field_name,
            )

    # ------------------------------------------------------------------
    # 3. List views — Description must exist but be hidden by default
    #    (optional='hide'), in BOTH inherited trees.
    # ------------------------------------------------------------------
    def _assert_description_optional_hidden(self, view_xmlid):
        view = self.env.ref(view_xmlid)
        arch = self.SaleOrder.get_view(view.id, "list")["arch"]
        tree = etree.fromstring(arch)
        nodes = tree.xpath("//field[@name='sale_description']")
        self.assertTrue(
            nodes, "Description column missing from %s" % view_xmlid
        )
        self.assertEqual(
            nodes[0].get("optional"),
            "hide",
            "Description column in %s must default to hidden (optional='hide')"
            % view_xmlid,
        )

    def test_description_column_hidden_by_default_in_quotation_tree(self):
        self._assert_description_optional_hidden(
            "sale.view_quotation_tree_with_onboarding"
        )

    def test_description_column_hidden_by_default_in_order_tree(self):
        self._assert_description_optional_hidden("sale.view_order_tree")

    # ------------------------------------------------------------------
    # 4. Translation — guards the i18n/es.po we ship.
    # ------------------------------------------------------------------
    def test_spanish_field_label_is_translated(self):
        fields_es = self.SaleOrder.with_context(lang="es_ES").fields_get(
            ["sale_description", "customer_purchase_order"]
        )
        self.assertEqual(fields_es["sale_description"]["string"], "Descripción")
        self.assertEqual(
            fields_es["customer_purchase_order"]["string"],
            "Orden de Compra del Cliente",
        )
