# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class PickingType(models.Model):
    _inherit = "stock.picking.type"

    auto_invoice = fields.Boolean(
        string="Generate Invoice",
        default=False,
        help="If checked, allows creating invoices directly from the picking view."
    )
    auto_invoice_on_validate = fields.Boolean(
        string="Auto-invoice on Validation",
        default=False,
        help="If checked, automatically triggers the invoice creation flow after validating the picking."
    )
