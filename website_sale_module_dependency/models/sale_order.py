import logging

from odoo import _, models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _find_matching_dep_variant(self, source_product, dep_template):
        """Find the dependency variant matching the source product's attributes.

        Compares the raw ``product.attribute.value`` records of the source
        variant with each variant of *dep_template* and returns the one whose
        attribute values have the greatest overlap (e.g. same "Odoo Version").

        Falls back to the first variant when:
        * the dependency template has a single (or no) variant, or
        * none of the dependency variants share any attribute value with the
          source product.

        :param product.product source_product: the variant added to the cart.
        :param product.template dep_template: the dependency template.
        :return: best-matching variant of ``dep_template``.
        :rtype: product.product
        """
        source_attr_values = (
            source_product.product_template_attribute_value_ids
            .product_attribute_value_id
        )

        # Short-circuit: no attributes to compare or single variant
        if not source_attr_values or len(dep_template.product_variant_ids) <= 1:
            return dep_template.product_variant_id

        best_match = self.env['product.product']
        best_score = 0
        for variant in dep_template.product_variant_ids:
            variant_attr_values = (
                variant.product_template_attribute_value_ids
                .product_attribute_value_id
            )
            score = len(source_attr_values & variant_attr_values)
            if score > best_score:
                best_score = score
                best_match = variant

        return best_match or dep_template.product_variant_id

    # ------------------------------------------------------------------
    # Cart: auto-add dependencies
    # ------------------------------------------------------------------
    def _cart_update(self, product_id, line_id=None, add_qty=0, set_qty=0, **kwargs):
        """Override to auto-add module dependencies to the cart.

        After the main product is added via super(), if the product is an Odoo
        module with dependencies, each missing dependency is also added as a
        separate cart line (qty=1).  Dependencies are resolved recursively.

        When a module is **removed** from the cart, orphan dependency lines
        that are no longer required by any other module in the cart are also
        removed automatically.

        Variant-aware: the dependency variant whose attribute values best match
        the source product (e.g. same Odoo version) is selected.  Already-
        present dependencies are detected at *variant* level to support
        products with multiple variants in the same cart.
        """
        product = self.env['product.product'].browse(product_id).exists()
        if not product:
            return super()._cart_update(
                product_id, line_id=line_id,
                add_qty=add_qty, set_qty=set_qty, **kwargs,
            )

        template = product.product_tmpl_id

        result = super()._cart_update(
            product_id,
            line_id=line_id,
            add_qty=add_qty,
            set_qty=set_qty,
            **kwargs,
        )

        # ── REMOVAL: auto-cleanup orphan dependencies ──
        # Detect removal: result quantity is 0 and the main line no longer
        # exists in the order.
        result_qty = result.get('quantity', 1)
        if result_qty <= 0 and template.is_odoo_module:
            self._cleanup_orphan_dependencies(template)
            return result

        # ── ADDITION: auto-add missing dependencies ──
        if not add_qty or add_qty <= 0:
            if not set_qty or set_qty <= 0:
                return result

        if not template.is_odoo_module or not template.all_dependency_ids:
            return result

        # Detect duplicates at variant level (product_id)
        cart_product_ids = set(
            self.order_line.mapped('product_id').ids
        )

        deps_added = 0
        for dep_template in template.all_dependency_ids:
            # Find the best-matching variant for this dependency
            dep_product = self._find_matching_dep_variant(product, dep_template)
            if not dep_product:
                _logger.warning(
                    "MODULE DEP: Dependency [%s] has no variant, skipping.",
                    dep_template.display_name,
                )
                continue

            if dep_product.id in cart_product_ids:
                continue  # Already in cart, skip

            # Skip unpublished / inactive / non-salable dependencies.
            # NOTE: we check fields directly instead of using
            # _is_add_to_cart_allowed() because that method returns True
            # for sudo() users (group_system bypass).
            if not (dep_product.active
                    and dep_product.sale_ok
                    and dep_template.website_published):
                _logger.warning(
                    "MODULE DEP: Dependency [%s] is not published or not "
                    "salable, skipping auto-add.",
                    dep_product.display_name,
                )
                continue

            # Add the dependency to the cart (qty=1)
            super()._cart_update(
                product_id=dep_product.id,
                add_qty=1,
            )
            deps_added += 1

        if deps_added:
            _logger.info(
                "MODULE DEP: Added %d dependencies to cart for [%s].",
                deps_added,
                product.display_name,
            )

        return result

    # ------------------------------------------------------------------
    # Cart: cleanup orphan dependencies on removal
    # ------------------------------------------------------------------
    def _cleanup_orphan_dependencies(self, removed_template):
        """Remove dependency lines that are no longer needed by any module.

        When a parent module is removed from the cart, its dependency lines
        should be removed too — UNLESS another module in the cart still
        requires them.

        Uses ``order_line.unlink()`` directly because Odoo 18's
        ``_cart_update(set_qty=0)`` treats 0 as falsy and does not
        actually remove the line.

        :param product.template removed_template: the template being removed.
        """
        if not removed_template.all_dependency_ids:
            return

        removed_dep_tmpl_ids = set(removed_template.all_dependency_ids.ids)

        # Collect all deps still needed by other modules in the cart
        # that are NOT themselves dependencies of the removed module.
        still_needed = set()
        for line in self.order_line:
            line_tmpl = line.product_id.product_tmpl_id
            if line_tmpl.id == removed_template.id:
                continue
            if line_tmpl.id not in removed_dep_tmpl_ids:
                # This line is NOT a dep of the removed module — keep
                # it and all of its own dependencies safe.
                still_needed.add(line_tmpl.id)
                if line_tmpl.is_odoo_module and line_tmpl.all_dependency_ids:
                    still_needed |= set(line_tmpl.all_dependency_ids.ids)

        # Deps to remove = removed module's deps − deps still needed
        orphan_tmpl_ids = removed_dep_tmpl_ids - still_needed

        if not orphan_tmpl_ids:
            return

        # Find and remove orphan lines via unlink
        lines_to_remove = self.order_line.filtered(
            lambda l: l.product_id.product_tmpl_id.id in orphan_tmpl_ids
        )
        if lines_to_remove:
            _logger.info(
                "MODULE DEP: Removing %d orphan dependency lines from cart.",
                len(lines_to_remove),
            )
            lines_to_remove.sudo().unlink()

    # ------------------------------------------------------------------
    # Backend: Add Dependencies button
    # ------------------------------------------------------------------
    def action_add_dependencies(self):
        """Add missing module dependencies as new order lines.

        Scans all order lines that contain Odoo modules, resolves their
        full recursive dependency tree, and creates new SO lines for any
        dependency not yet present.

        Variant-aware: uses ``_find_matching_dep_variant`` to pick the
        variant whose attribute values best match the source product.

        :return: notification action with the result summary.
        :rtype: dict
        """
        self.ensure_one()

        # Gather all module templates and their products already in the order
        existing_tmpl_ids = set()
        module_lines = []
        for line in self.order_line:
            tmpl = line.product_id.product_tmpl_id
            existing_tmpl_ids.add(tmpl.id)
            if tmpl.is_odoo_module and tmpl.all_dependency_ids:
                module_lines.append(line)

        if not module_lines:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Module Dependencies"),
                    'message': _("No Odoo modules with dependencies found in this order."),
                    'type': 'info',
                    'sticky': False,
                },
            }

        # Collect all missing dependencies
        SaleOrderLine = self.env['sale.order.line']
        added_names = []
        unpublished_names = []

        for line in module_lines:
            source_product = line.product_id
            tmpl = source_product.product_tmpl_id

            for dep_template in tmpl.all_dependency_ids:
                if dep_template.id in existing_tmpl_ids:
                    continue  # Already in order

                dep_product = self._find_matching_dep_variant(
                    source_product, dep_template,
                )
                if not dep_product:
                    _logger.warning(
                        "MODULE DEP BACKEND: Dependency [%s] has no variant.",
                        dep_template.display_name,
                    )
                    continue

                # Create the order line
                SaleOrderLine.create({
                    'order_id': self.id,
                    'product_id': dep_product.id,
                    'product_uom_qty': 1,
                })
                existing_tmpl_ids.add(dep_template.id)
                added_names.append(dep_product.display_name)

                if not dep_template.website_published:
                    unpublished_names.append(dep_product.display_name)

        # Build notification message
        if not added_names:
            message = _("All dependencies are already satisfied. ✓")
            notif_type = 'success'
        else:
            message = _(
                "Added %(count)d dependency(ies): %(names)s",
                count=len(added_names),
                names=", ".join(added_names),
            )
            if unpublished_names:
                message += _("\n⚠ Not published on website: %s", ", ".join(unpublished_names))
            notif_type = 'success'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Module Dependencies"),
                'message': message,
                'type': notif_type,
                'sticky': bool(added_names),
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }
