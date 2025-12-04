from odoo import _, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    allow_invoice_without_delivery = fields.Boolean(
        string="Allow Invoice Without Delivery",
        default=False,
        groups='sale_flexible_invoice_policy.group_allow_invoice_without_delivery',
        tracking=True,
        help="When enabled, allows invoicing this order as if all products had "
             "'Ordered quantities' policy, regardless of actual product configuration. "
             "This bypasses the delivery requirement for products with 'Delivered quantities' policy."
    )

    def _create_invoices(self, grouped=False, final=False, date=None):
        """
        Override to force invoice policy to 'order' when allow_invoice_without_delivery is enabled.
        This must be done BEFORE _get_invoiceable_lines() is called.
        """
        # Apply force policy for orders with the flag enabled
        orders_with_exception_ids = self.sudo().filtered(lambda o: o.allow_invoice_without_delivery).ids
        orders_with_exception = self.browse(orders_with_exception_ids)
        if orders_with_exception:
            orders_with_exception._force_lines_to_invoice_policy_order()
        
        # Call parent method to proceed with invoice creation
        invoices = super()._create_invoices(grouped=grouped, final=final, date=date)
        
        # Auto-cleanup: Reset flag after invoice creation if configured
        if orders_with_exception:
            auto_cleanup = self.env['ir.config_parameter'].sudo().get_param(
                'sale_flexible_invoice_policy.auto_cleanup_flag',
                default='True'
            )
            
            if auto_cleanup == 'True':
                # Disable tracking temporarily to avoid duplicate messages
                for order in orders_with_exception:
                    order.with_context(tracking_disable=True).allow_invoice_without_delivery = False
                    # Post custom message in chatter explaining auto-reset
                    order.message_post(
                        body=_('The "Allow Invoice Without Delivery" flag has been automatically disabled for security after invoice creation.'),
                        message_type='notification',
                        subtype_xmlid='mail.mt_note'
                    )
        
        return invoices
