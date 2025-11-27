from odoo import models

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def _create_invoices(self, sale_orders):
        """
        Override to automatically post invoices if configured on the Sales Team.
        """
        invoices = super(SaleAdvancePaymentInv, self)._create_invoices(sale_orders)
        
        # Check if we should auto-post invoices
        # We check the team of the first order, assuming batch invoicing usually happens for same team
        # or we iterate. Since invoices are created, we can check their team.
        
        for invoice in invoices:
            if invoice.team_id and invoice.team_id.create_posted_invoice:
                if invoice.state == 'draft':
                    invoice.action_post()
                    
        return invoices
