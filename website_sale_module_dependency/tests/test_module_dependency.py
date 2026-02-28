# Copyright 2026 Ganemo
# License OPL-1

import odoo.tests

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


@odoo.tests.tagged('post_install', '-at_install')
class TestModuleDependency(TransactionCase):
    """Tests for website_sale_module_dependency.

    Covers: recursive dependency resolution, cycle protection,
    circular constraint, cached dependencies, total price computation,
    cart auto-add logic, cart auto-cleanup, and variant-aware
    dependency matching.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ProductTemplate = cls.env['product.template']

        # Module C — no dependencies (leaf)
        cls.module_c = ProductTemplate.create({
            'name': 'Module C - Base Utils',
            'is_odoo_module': True,
            'technical_module_name': 'base_utils',
            'list_price': 25.0,
            'type': 'service',
            'website_published': True,
        })

        # Module B — depends on C
        cls.module_b = ProductTemplate.create({
            'name': 'Module B - Connector',
            'is_odoo_module': True,
            'technical_module_name': 'connector',
            'list_price': 50.0,
            'type': 'service',
            'website_published': True,
            'dependency_ids': [(6, 0, [cls.module_c.id])],
        })

        # Module A — depends on B (which depends on C)
        cls.module_a = ProductTemplate.create({
            'name': 'Module A - Full Suite',
            'is_odoo_module': True,
            'technical_module_name': 'full_suite',
            'list_price': 100.0,
            'type': 'service',
            'website_published': True,
            'dependency_ids': [(6, 0, [cls.module_b.id])],
        })

        # Regular product — not an Odoo module
        cls.regular_product = ProductTemplate.create({
            'name': 'Regular Product',
            'is_odoo_module': False,
            'list_price': 200.0,
            'type': 'service',
        })

        # Create a website for sale.order
        cls.website = cls.env['website'].search([], limit=1)
        if not cls.website:
            cls.website = cls.env['website'].create({
                'name': 'Test Website',
            })

        # Create a partner for sale orders
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Customer',
        })

        # ── Variant-aware test data ──
        # Create "Odoo Version" attribute with values "17.0" and "18.0"
        cls.version_attr = cls.env['product.attribute'].create({
            'name': 'Odoo Version',
            'create_variant': 'always',
        })
        cls.version_17 = cls.env['product.attribute.value'].create({
            'name': '17.0',
            'attribute_id': cls.version_attr.id,
        })
        cls.version_18 = cls.env['product.attribute.value'].create({
            'name': '18.0',
            'attribute_id': cls.version_attr.id,
        })

        # Module Y — leaf dependency with 17.0 and 18.0 variants
        cls.module_y = ProductTemplate.create({
            'name': 'Module Y - Dependency',
            'is_odoo_module': True,
            'technical_module_name': 'module_y',
            'list_price': 30.0,
            'type': 'service',
            'website_published': True,
            'attribute_line_ids': [(0, 0, {
                'attribute_id': cls.version_attr.id,
                'value_ids': [(6, 0, [cls.version_17.id, cls.version_18.id])],
            })],
        })

        # Module X — depends on Module Y, also has 17.0 and 18.0 variants
        cls.module_x = ProductTemplate.create({
            'name': 'Module X - Main Module',
            'is_odoo_module': True,
            'technical_module_name': 'module_x',
            'list_price': 80.0,
            'type': 'service',
            'website_published': True,
            'attribute_line_ids': [(0, 0, {
                'attribute_id': cls.version_attr.id,
                'value_ids': [(6, 0, [cls.version_17.id, cls.version_18.id])],
            })],
            'dependency_ids': [(6, 0, [cls.module_y.id])],
        })

    # ------------------------------------------------------------------
    # Dependency resolution tests
    # ------------------------------------------------------------------
    def test_get_all_dependencies_simple(self):
        """Module B depends on C. _get_all_dependencies returns {C}."""
        deps = self.module_b._get_all_dependencies()
        self.assertEqual(deps, self.module_c)

    def test_get_all_dependencies_recursive(self):
        """Module A depends on B→C. _get_all_dependencies returns {B, C}."""
        deps = self.module_a._get_all_dependencies()
        self.assertEqual(
            set(deps.ids),
            {self.module_b.id, self.module_c.id},
            "Should recursively resolve B and C as dependencies of A.",
        )


    def test_get_all_dependencies_no_deps(self):
        """Module C has no dependencies. Returns empty recordset."""
        deps = self.module_c._get_all_dependencies()
        self.assertFalse(deps, "Module with no dependency_ids should return empty.")

    # ------------------------------------------------------------------
    # Circular dependency constraint tests
    # ------------------------------------------------------------------
    def test_circular_dependency_constraint_direct(self):
        """A module cannot depend on itself."""
        with self.assertRaises(ValidationError):
            self.module_c.dependency_ids = [(4, self.module_c.id)]

    def test_circular_dependency_constraint_indirect(self):
        """Creating A→B→C→A should raise ValidationError."""
        with self.assertRaises(ValidationError):
            self.module_c.dependency_ids = [(4, self.module_a.id)]

    # ------------------------------------------------------------------
    # Cached all_dependency_ids tests
    # ------------------------------------------------------------------
    def test_cached_all_dependency_ids_simple(self):
        """Module B's all_dependency_ids should contain C."""
        self.assertEqual(
            set(self.module_b.all_dependency_ids.ids),
            {self.module_c.id},
        )

    def test_cached_all_dependency_ids_chain(self):
        """Module A's all_dependency_ids should contain B and C."""
        self.assertEqual(
            set(self.module_a.all_dependency_ids.ids),
            {self.module_b.id, self.module_c.id},
        )

    def test_cached_all_dependency_ids_no_deps(self):
        """Module C has no all_dependency_ids."""
        self.assertFalse(self.module_c.all_dependency_ids)

    def test_cached_all_dependency_ids_regular_product(self):
        """Regular product has no all_dependency_ids."""
        self.assertFalse(self.regular_product.all_dependency_ids)

    # ------------------------------------------------------------------
    # Price computation tests
    # ------------------------------------------------------------------
    def test_total_price_with_deps_simple(self):
        """Module B ($50) + C ($25) = $75."""
        self.assertEqual(
            self.module_b.total_price_with_deps, 75.0,
            "B($50) + C($25) = $75",
        )

    def test_total_price_with_deps_chain(self):
        """Module A ($100) + B ($50) + C ($25) = $175."""
        self.assertEqual(
            self.module_a.total_price_with_deps, 175.0,
            "A($100) + B($50) + C($25) = $175",
        )

    def test_total_price_no_deps(self):
        """Module C has no deps; total_price = its own list_price."""
        self.assertEqual(
            self.module_c.total_price_with_deps, 25.0,
            "Module with no deps should equal its own price.",
        )

    def test_total_price_regular_product(self):
        """Regular product: total_price = its own list_price."""
        self.assertEqual(
            self.regular_product.total_price_with_deps, 200.0,
            "Non-module product should equal its own price.",
        )

    def test_dependency_count(self):
        """Module A should have 2 recursive dependencies (B and C)."""
        self.assertEqual(self.module_a.dependency_count, 2)
        self.assertEqual(self.module_b.dependency_count, 1)
        self.assertEqual(self.module_c.dependency_count, 0)
        self.assertEqual(self.regular_product.dependency_count, 0)

    # ------------------------------------------------------------------
    # Cart update tests
    # ------------------------------------------------------------------
    def _create_sale_order(self):
        """Create a draft sale.order tied to the test website."""
        return self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'website_id': self.website.id,
        })

    def test_cart_update_adds_dependencies(self):
        """Adding Module A to cart should also add B and C."""
        order = self._create_sale_order()
        product_a = self.module_a.product_variant_id

        order._cart_update(product_id=product_a.id, add_qty=1)

        cart_tmpl_ids = set(order.order_line.mapped('product_template_id').ids)
        self.assertIn(self.module_a.id, cart_tmpl_ids, "Module A should be in cart.")
        self.assertIn(self.module_b.id, cart_tmpl_ids, "Module B (dep) should be in cart.")
        self.assertIn(self.module_c.id, cart_tmpl_ids, "Module C (dep of dep) should be in cart.")
        self.assertEqual(len(order.order_line), 3, "Cart should have exactly 3 lines.")

    def test_cart_update_no_duplicate_deps(self):
        """If Module B is already in cart, adding A should not duplicate B."""
        order = self._create_sale_order()
        product_b = self.module_b.product_variant_id
        product_a = self.module_a.product_variant_id

        # First add B (which will also add C)
        order._cart_update(product_id=product_b.id, add_qty=1)
        self.assertEqual(len(order.order_line), 2, "B + C = 2 lines.")

        # Now add A — should only add A itself (B and C already present)
        order._cart_update(product_id=product_a.id, add_qty=1)
        self.assertEqual(
            len(order.order_line), 3,
            "A + B + C = 3 lines (no duplicates).",
        )

    def test_cart_update_regular_product_unaffected(self):
        """Adding a regular product should not trigger dependency logic."""
        order = self._create_sale_order()
        product = self.regular_product.product_variant_id

        order._cart_update(product_id=product.id, add_qty=1)
        self.assertEqual(
            len(order.order_line), 1,
            "Regular product should create exactly 1 cart line.",
        )

    # ------------------------------------------------------------------
    # Cart cleanup tests
    # ------------------------------------------------------------------
    def test_cart_cleanup_on_remove(self):
        """Removing Module A should also remove its orphan deps B and C."""
        order = self._create_sale_order()
        product_a = self.module_a.product_variant_id

        # Add A (auto-adds B and C)
        order._cart_update(product_id=product_a.id, add_qty=1)
        self.assertEqual(len(order.order_line), 3)

        # Remove A (should remove B and C too)
        line_a = order.order_line.filtered(
            lambda l: l.product_id == product_a
        )
        order._cart_update(
            product_id=product_a.id,
            line_id=line_a.id,
            add_qty=None,
            set_qty=0,
        )
        self.assertEqual(
            len(order.order_line), 0,
            "All dependency lines should be removed when the parent is removed.",
        )

    def test_cart_cleanup_shared_dep_preserved(self):
        """Shared deps should NOT be removed when still needed by another module.

        Scenario: Module D depends on C (which is also A's transitive dep).
        When A is removed, C should stay because D still needs it.
        """
        # Create Module D — depends on C (shared dep with A→B→C)
        module_d = self.env['product.template'].create({
            'name': 'Module D - Reports',
            'is_odoo_module': True,
            'technical_module_name': 'reports',
            'list_price': 40.0,
            'type': 'service',
            'website_published': True,
            'dependency_ids': [(6, 0, [self.module_c.id])],
        })

        order = self._create_sale_order()
        product_a = self.module_a.product_variant_id
        product_d = module_d.product_variant_id

        # Add D first (auto-adds C) — 2 lines
        order._cart_update(product_id=product_d.id, add_qty=1)
        self.assertEqual(len(order.order_line), 2)

        # Add A (auto-adds B; C already present) — 4 lines total
        order._cart_update(product_id=product_a.id, add_qty=1)
        self.assertEqual(len(order.order_line), 4)

        # Remove A — B should be removed (orphan dep of A only),
        # but C should stay (D still needs it), and D stays too
        line_a = order.order_line.filtered(
            lambda l: l.product_id == product_a
        )
        order._cart_update(
            product_id=product_a.id,
            line_id=line_a.id,
            add_qty=None,
            set_qty=0,
        )
        remaining_tmpl_ids = set(
            order.order_line.mapped('product_template_id').ids
        )
        self.assertIn(
            module_d.id, remaining_tmpl_ids,
            "Module D should remain — it was independently added.",
        )
        self.assertIn(
            self.module_c.id, remaining_tmpl_ids,
            "Module C should remain — it's still needed by Module D.",
        )
        self.assertNotIn(
            self.module_b.id, remaining_tmpl_ids,
            "Module B should be removed — no other module needs it.",
        )
        self.assertNotIn(
            self.module_a.id, remaining_tmpl_ids,
            "Module A should be removed — it was explicitly deleted.",
        )

    # ------------------------------------------------------------------
    # Variant-aware cart tests
    # ------------------------------------------------------------------
    def _get_variant_by_value(self, template, attr_value):
        """Return the product.product variant matching the given attr value."""
        for variant in template.product_variant_ids:
            attr_values = (
                variant.product_template_attribute_value_ids
                .product_attribute_value_id
            )
            if attr_value in attr_values:
                return variant
        return self.env['product.product']

    def test_cart_adds_matching_variant(self):
        """Adding Module X (18.0) should add Module Y (18.0) as dependency."""
        order = self._create_sale_order()

        # Get the 18.0 variant of Module X
        product_x_18 = self._get_variant_by_value(self.module_x, self.version_18)
        self.assertTrue(product_x_18, "Module X should have an 18.0 variant.")

        # Get the 18.0 variant of Module Y (expected dep)
        product_y_18 = self._get_variant_by_value(self.module_y, self.version_18)
        self.assertTrue(product_y_18, "Module Y should have an 18.0 variant.")

        order._cart_update(product_id=product_x_18.id, add_qty=1)

        cart_product_ids = set(order.order_line.mapped('product_id').ids)
        self.assertIn(
            product_x_18.id, cart_product_ids,
            "Module X (18.0) should be in cart.",
        )
        self.assertIn(
            product_y_18.id, cart_product_ids,
            "Module Y (18.0) should be auto-added — not a random variant.",
        )
        self.assertEqual(len(order.order_line), 2, "Cart should have exactly 2 lines.")

    def test_cart_adds_17_variant_when_adding_17(self):
        """Adding Module X (17.0) should add Module Y (17.0) as dependency."""
        order = self._create_sale_order()

        product_x_17 = self._get_variant_by_value(self.module_x, self.version_17)
        product_y_17 = self._get_variant_by_value(self.module_y, self.version_17)

        order._cart_update(product_id=product_x_17.id, add_qty=1)

        cart_product_ids = set(order.order_line.mapped('product_id').ids)
        self.assertIn(product_y_17.id, cart_product_ids,
                       "Module Y (17.0) should be auto-added for X (17.0).")

    def test_cart_no_variants_unchanged(self):
        """Products without variants (single variant) should work as before."""
        order = self._create_sale_order()
        product_a = self.module_a.product_variant_id

        order._cart_update(product_id=product_a.id, add_qty=1)

        cart_tmpl_ids = set(order.order_line.mapped('product_template_id').ids)
        self.assertIn(self.module_a.id, cart_tmpl_ids)
        self.assertIn(self.module_b.id, cart_tmpl_ids)
        self.assertIn(self.module_c.id, cart_tmpl_ids)
