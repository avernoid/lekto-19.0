from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payment_control_active = fields.Boolean(
        string="Active Payment Control",
        copy=False,
        help="Check this box to enable the delivery blocking mechanism based on payment status for this specific order. Defaults are loaded from the Customer or Sales Team."
    )
    payment_validation_level = fields.Selection(
        [('sale', 'Sale Order Level'), ('picking', 'Picking Level')],
        string="Validation Level",
        default='sale',
        copy=False,
        help="Select 'Sale Order Level' to validate based on the total order payment status, or 'Picking Level' to validate based on the specific value of goods in the picking."
    )
    include_credit_analysis = fields.Boolean(
        string="Include Credit Analysis",
        default=True,
        copy=False,
        help="If checked, the system will consider the partner's credit terms. If the credit is not due (payment term days > 0), validation will be allowed even if unpaid."
    )
    require_full_payment = fields.Boolean(
        string="Require Full Payment",
        default=False,
        copy=False,
        help="If checked, the delivery will only be allowed if the order (or picking value) is 100% paid. Partial payments will block validation."
    )
    payment_coverage_status = fields.Selection(
        [
            ('no_control', 'No Control'),
            ('not_covered', 'Not Covered'),
            ('partially_covered', 'Partially Covered'),
            ('fully_covered', 'Fully Covered'),
            ('credit_not_due', 'Credit Not Due')
        ],
        string="Payment Coverage",
        compute='_compute_payment_coverage_status',
        store=True,
        help="The current calculated payment status. 'Fully Covered' means paid or within credit terms 'Not Covered' means payment is required."
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'payment_control_active' not in vals:
                partner_id = vals.get('partner_id')
                team_id = vals.get('team_id')
                
                source = None
                
                # Check Partner first
                if partner_id:
                     partner = self.env['res.partner'].browse(partner_id)
                     if partner.payment_control_active:
                         source = partner
                
                # Check Team second if no source found
                if not source and team_id:
                    team = self.env['crm.team'].browse(team_id)
                    if team.payment_control_active:
                        source = team
                
                # Apply defaults if source found
                if source:
                    vals['payment_control_active'] = True
                    vals['payment_validation_level'] = source.payment_validation_level
                    vals['include_credit_analysis'] = source.include_credit_analysis
                    vals['require_full_payment'] = source.require_full_payment
                else:
                    vals['payment_control_active'] = False

        return super().create(vals_list)

    @api.onchange('partner_id')
    def _onchange_partner_payment_control(self):
        # Do not overwrite if already active (considered "defined")
        if self.payment_control_active:
            return
        
        if self.partner_id and self.partner_id.payment_control_active:
            self.payment_control_active = True
            self.payment_validation_level = self.partner_id.payment_validation_level
            self.include_credit_analysis = self.partner_id.include_credit_analysis
            self.require_full_payment = self.partner_id.require_full_payment
        elif self.team_id and self.team_id.payment_control_active:
             # Fallback to team if partner has no control but team does?
             # Requirement: Partner -> Team.
             # If Partner has NO control (False), should we fall back to Team?
             # "Si ninguno define política -> False".
             # If Partner is set, it defines the policy (even if it is False?)
             # "Si ninguno define política". 
             # If Partner.payment_control_active is False, does it mean "No Policy" or "Policy is OFF"?
             # Usually booleans: False is "OFF"/"No".
             # So if Partner is False, we check Team.
             self.payment_control_active = True
             self.payment_validation_level = self.team_id.payment_validation_level
             self.include_credit_analysis = self.team_id.include_credit_analysis
             self.require_full_payment = self.team_id.require_full_payment

    @api.onchange('team_id')
    def _onchange_team_payment_control(self):
         if self.payment_control_active:
            return
         
         # Only apply team defaults if Partner didn't set it (which is handled by the guard above)
         # and if we don't have a partner yet or partner didn't trigger?
         # If partner is set but yielded False, should Team override?
         # Same logic as above.
         if self.team_id and self.team_id.payment_control_active:
             # Check if partner prevents this?
             # If I have a partner, and partner is "Active=False", does that mean we shouldn't use Team?
             # Priority: Client > Team.
             # If Client.Active is False, does that mean "Client says NO CONTROL" or "Client has no opinion"?
             # Given "Si ninguno define política", it implies False = No Opinion/No Policy.
             # So we use Team.
             self.payment_control_active = True
             self.payment_validation_level = self.team_id.payment_validation_level
             self.include_credit_analysis = self.team_id.include_credit_analysis
             self.require_full_payment = self.team_id.require_full_payment

    @api.depends('order_line', 'invoice_ids.payment_state', 'payment_term_id')
    def _compute_payment_coverage_status(self):
        for order in self:
            if not order.payment_control_active:
                order.payment_coverage_status = 'no_control'
                continue

            total_amount = order.amount_total
            if total_amount == 0:
                order.payment_coverage_status = 'fully_covered'
                continue

            # Calculate total paid
            total_paid = sum(order.invoice_ids.filtered(lambda inv: inv.state == 'posted').mapped('amount_total')) - \
                         sum(order.invoice_ids.filtered(lambda inv: inv.state == 'posted').mapped('amount_residual'))
            
            # Check credit
            # Simplified credit check logic - assumes standard Odoo payment terms
            is_credit = False
            if order.include_credit_analysis and order.payment_term_id:
                # Heuristic: if payment term has lines with days > 0, it's credit
                if any(line.nb_days > 0 for line in order.payment_term_id.line_ids):
                    is_credit = True

            if total_paid >= total_amount:
                order.payment_coverage_status = 'fully_covered'
            elif total_paid > 0:
                 if order.require_full_payment:
                     order.payment_coverage_status = 'partially_covered' # Treat as not enough if full req
                 else:
                     order.payment_coverage_status = 'partially_covered'
            else:
                if is_credit:
                    order.payment_coverage_status = 'credit_not_due'
                else:
                    order.payment_coverage_status = 'not_covered'
