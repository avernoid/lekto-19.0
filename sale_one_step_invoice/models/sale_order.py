from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_create_invoice(self):
        """
        Override to optionally skip the invoice wizard and auto-post the invoice
        based on the Sales Team configuration.
        """
        # Check if we should skip the wizard for this order's team
        if self.team_id and self.team_id.skip_invoice_wizard:
            # Create the invoice wizard with default values (advance_payment_method='delivered')
            payment = self.env['sale.advance.payment.inv'].with_context(active_ids=self.ids, active_model='sale.order').create({
                'advance_payment_method': 'delivered',
                'sale_order_ids': [fields.Command.set(self.ids)],
            })
            
            # Call create_invoices on the wizard to generate the invoice
            # The wizard's _create_invoices method (overridden in sale_advance_payment_inv.py)
            # will handle the auto-posting if configured.
            action = payment.create_invoices()
            
            return action
        
        # Fallback to standard behavior: Open the wizard
        # We use the XML ID of the action that the button originally called
        return self.env['ir.actions.act_window']._for_xml_id('sale.action_view_sale_advance_payment_inv')
