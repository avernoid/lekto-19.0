from odoo import models


class SaleOrder(models.Model):
    """Fields used by the Work Order report:

    - work_order_observations  → sale_custom_fields
    - customer_purchase_order  → sale_custom_fields
    - client_order_ref         → native Odoo
    """

    _inherit = "sale.order"
