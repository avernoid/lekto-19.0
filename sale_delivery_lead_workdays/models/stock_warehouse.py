# Part of Ganemo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    resource_calendar_id = fields.Many2one(
        comodel_name="resource.calendar",
        string="Delivery Working Calendar",
        check_company=True,
        help="Working calendar used to translate a delivery lead time expressed "
        "in working days into calendar days, skipping non-working days and "
        "holidays. Holidays are read from the global time off and from this "
        "calendar's own time off. If left empty, no working-day conversion is "
        "done and the order's value is written to the lines as plain days.",
    )
    delivery_lead_workdays = fields.Integer(
        string="Default Delivery Lead Time (Working Days)",
        help="Default number of working days proposed on new sales orders "
        "shipping from this warehouse. It only sets the default; it can be "
        "overridden on each order.",
    )
