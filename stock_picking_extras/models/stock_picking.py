# -*- coding: utf-8 -*-
from odoo import api, fields, models

class StockPicking(models.Model):
    _inherit = "stock.picking"

    total_packages = fields.Integer(
        string="Total Packages",
        compute="_compute_logistics_info",
        store=True,
        readonly=True,
        help="This field displays the total count of unique packages associated with the moves in this transfer. It is automatically computed based on the 'Destination Package' set on the detailed operations."
    )
    total_bundles = fields.Integer(
        string="Total Bundles",
        compute="_compute_logistics_info",
        store=True,
        readonly=True,
        help="Represents the total number of handling units (bundles) for logistics. Calculation Rule: Each unique Package counts as 1 Bundle. For items not in a package (loose), each unit of product quantity counts as 1 Bundle."
    )

    @api.depends('move_line_ids.result_package_id', 'move_line_ids.quantity')
    def _compute_logistics_info(self):
        for picking in self:
            packages = set()
            bundles_from_lines = 0.0

            for line in picking.move_line_ids:
                if line.result_package_id:
                    packages.add(line.result_package_id.id)
                else:
                    # Requirement: "Líneas sin paquete: cada unidad de cantidad cuenta como 1 bulto"
                    # Assumption: We sum the quantity (count of units).
                    bundles_from_lines += line.quantity

            total_packages_count = len(packages)
            
            # Total bundles calculation:
            # 1 package = 1 bundle
            # Loose items: sum of quantity
            # We round the loose quantity sum to avoid partial bundles if quantity is float.
            picking.total_packages = total_packages_count
            picking.total_bundles = total_packages_count + int(round(bundles_from_lines))
