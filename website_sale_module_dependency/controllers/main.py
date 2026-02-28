import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class WebsiteSaleModuleDependency(http.Controller):

    @http.route(
        '/shop/module_deps_prices',
        type='json',
        auth='public',
        website=True,
    )
    def get_dependency_prices(self, product_template_ids):
        """Return pricelist-aware prices for module dependencies.

        Uses the same pricing pipeline as website_sale (pricelist +
        fiscal position + tax included/excluded), so the prices shown
        will match what the visitor sees in the cart.

        :param list product_template_ids: ids of the templates to compute prices for.
        :return: dict keyed by template id with dependency price data.
        """
        website = request.website
        pricelist = website.pricelist_id
        currency = website.currency_id

        templates = (
            request.env['product.template']
            .sudo()
            .browse(product_template_ids)
            .exists()
        )

        # Collect ALL templates we need prices for (parents + deps)
        all_templates_needed = request.env['product.template'].sudo()
        deps_by_parent = {}
        for template in templates:
            if not template.is_odoo_module or not template.dependency_ids:
                continue
            all_deps = template._get_all_dependencies()
            if not all_deps:
                continue
            deps_by_parent[template.id] = all_deps
            all_templates_needed |= template | all_deps

        if not all_templates_needed:
            return {}

        # Compute pricelist prices for all templates in a single batch
        sales_prices = all_templates_needed._get_sales_prices(website)

        result = {}
        for tmpl_id, all_deps in deps_by_parent.items():
            parent_price_info = sales_prices.get(tmpl_id, {})
            parent_price = parent_price_info.get('price_reduce', 0.0)

            dep_list = []
            total = parent_price
            for dep in all_deps:
                dep_price_info = sales_prices.get(dep.id, {})
                dep_price = dep_price_info.get('price_reduce', 0.0)
                dep_list.append({
                    'id': dep.id,
                    'name': dep.name,
                    'price': dep_price,
                })
                total += dep_price

            result[str(tmpl_id)] = {
                'deps': dep_list,
                'total': total,
                'currency_symbol': currency.symbol,
                'currency_position': currency.position,
            }

        return result
