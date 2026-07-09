from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    sale_description = fields.Text(
        string="Description",
        help="Short summary of the quotation. It is shown as an optional "
             "column in the Quotations and Sales Orders list views so you "
             "can identify at a glance what each order is about, without "
             "opening it. Purely informational: it does not affect pricing, "
             "taxes or the order flow.",
    )

    customer_purchase_order = fields.Char(
        string="Customer Purchase Order",
        help="The customer's purchase-order (PO) number for this sale, when "
             "applicable. Record it once the customer confirms so the "
             "commercial reference stays attached to the order for invoicing "
             "and follow-up. It is stored for reference only.",
    )

    work_order_observations = fields.Text(
        string="Work Order Observations",
        help="Free-text notes for the operations team. This field is intended "
             "to be printed in the 'Observations' section of the Work Order "
             "report (Orden de Trabajo). Use it for shop-floor instructions or "
             "any remark the production team should see.",
    )
