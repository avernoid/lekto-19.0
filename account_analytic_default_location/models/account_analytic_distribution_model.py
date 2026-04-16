from odoo import models, fields, api


class AccountAnalyticDefault(models.Model):
    _inherit = 'account.analytic.distribution.model'

    origin_warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Origin Warehouse',
        help="Select the Warehouse from which the goods are being moved. "
             "This rule applies to Sales Orders, Purchase Orders, and Invoices."
    )

    origin_location_id = fields.Many2one(
        comodel_name='stock.location', 
        string='Origin Location',
        help="Select the specific Source Location. This rule applies to stock-related documents like Sale Orders and Invoices."
    )

    dest_location_id = fields.Many2one(
        comodel_name='stock.location', 
        string='Destination Location',
        help="Select the specific Destination Location. Applies to documents involving stock moves."
    )
    
    invoice_user_id = fields.Many2one(
        comodel_name='res.users',
        string='Salesperson (Invoice)',
        help="Specific matching for the Salesperson on Customer Invoices. "
             "Warning: This field does NOT match the Salesperson on Sale Orders (SO)."
    )
    
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Responsible User (Invoice)',
        help="Specific matching for the Responsible User on Invoices. "
             "Warning: This field does NOT apply to non-accounting documents."
    )
    
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Journal (Invoice)',
        help="Specific matching for the Accounting Journal. Only applies to Invoices/Bills."
    )



    @api.model
    def _get_default_search_domain_vals(self):
        res = super()._get_default_search_domain_vals()
        res.update({
            'origin_warehouse_id': False,
            'origin_location_id': False,
            'dest_location_id': False,
            'invoice_user_id': False,
            'user_id': False,
            'journal_id': False,
        })
        return res








