# -*- coding: utf-8 -*-
from odoo import api, fields, models

class StockPicking(models.Model):
    _inherit = "stock.picking"

    total_bundles = fields.Integer(
        string="Total Bundles",
        compute="_compute_logistics_info",
        store=True,
        readonly=True,
        help="Represents the total number of handling units (bundles) for logistics. Calculation Rule: Each unique Package counts as 1 Bundle. For items not in a package (loose), each unit of product quantity counts as 1 Bundle."
    )

    @api.depends('move_line_ids.result_package_id', 'move_line_ids.quantity', 'packages_count')
    def _compute_logistics_info(self):
        for picking in self:
            bundles_from_lines = 0.0

            for line in picking.move_line_ids:
                if not line.result_package_id:
                    # Requirement: "Líneas sin paquete: cada unidad de cantidad cuenta como 1 bulto"
                    # Assumption: We sum the quantity (count of units).
                    bundles_from_lines += line.quantity

            # Total bundles calculation:
            # 1 package = 1 bundle (using native packages_count)
            # Loose items: sum of quantity
            # We round the loose quantity sum to avoid partial bundles if quantity is float.
            picking.total_bundles = picking.packages_count + int(round(bundles_from_lines))
