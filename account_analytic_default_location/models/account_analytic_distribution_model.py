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
    def _get_distribution(self, arguments):
        """ Returns the combined distribution from all matching models.
            Refactored to match Odoo 19 merging logic + Multi-Prefix support.
        """
        # Discover all Many2one fields on the model (Dynamic Intelligence)
        dimension_fields = [
            fname for fname, field in self._fields.items()
            if field.type == 'many2one' 
            and not fname.startswith('create_') 
            and not fname.startswith('write_') 
            and fname != 'sequence'
        ]
        
        domain = []
        for field in dimension_fields + ['partner_category_id']:
            if field not in self._fields:
                continue
                
            value = arguments.get(field)
            if field == 'partner_category_id':
                domain += [(field, 'in', (value or []) + [False])]
            else:
                if value:
                    domain += [(field, 'in', [value, False])]
                else:
                    domain += [(field, '=', False)]

        # Search for candidate rules
        matching_rules = self.search(domain, order='sequence, id')
        
        target_account_code = str(arguments.get('account_prefix', ''))
        
        res = {}
        applied_plans = arguments.get('related_root_plan_ids', self.env['account.analytic.plan'])
        
        for rule in matching_rules:
            # 1. Match Account Prefix (Supports Multiple Prefixes "40, 60, 64")
            if rule.account_prefix:
                allowed_prefixes = [p.strip() for p in rule.account_prefix.split(',') if p.strip()]
                if not any(target_account_code.startswith(p) for p in allowed_prefixes):
                    continue 

            # 2. Merge logic (Odoo 19 style)
            # Combine distributions unless the plan is already filled by a higher priority rule
            rule_plans = rule.distribution_analytic_account_ids.root_plan_id
            if not applied_plans & rule_plans:
                res |= rule.analytic_distribution or {}
                applied_plans += rule_plans

        return res








