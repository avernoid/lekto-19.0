# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _

class Picking(models.Model):
    _inherit = "stock.picking"

    auto_invoice = fields.Boolean(related='picking_type_id.auto_invoice', readonly=True)
    auto_invoice_on_validate = fields.Boolean(related='picking_type_id.auto_invoice_on_validate', readonly=True)
    
    # Computed field to control button visibility safely (ignoring permissions)
    show_invoice_button = fields.Boolean(compute='_compute_show_invoice_button')
    
    # Smart button field
    invoice_count = fields.Integer(compute='_compute_invoice_count')

    def _compute_show_invoice_button(self):
        for picking in self:
            # Use sudo() to bypass access rules when checking sale_id
            picking_sudo = picking.sudo()
            picking.show_invoice_button = (
                picking_sudo.sale_id 
                and picking_sudo.auto_invoice 
                and not picking_sudo.auto_invoice_on_validate 
                and picking_sudo.state == 'done'
            )

    def _compute_invoice_count(self):
        for picking in self:
            # Use sudo() to bypass access rules when counting invoices
            picking_sudo = picking.sudo()
            if picking_sudo.sale_id:
                picking.invoice_count = len(picking_sudo.sale_id.invoice_ids)
            else:
                picking.invoice_count = 0

    def action_view_invoice(self):
        self.ensure_one()
        # Use sudo() to get the sale_id and its invoices
        picking_sudo = self.sudo()
        if not picking_sudo.sale_id:
            return
            
        invoices = picking_sudo.sale_id.invoice_ids
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
            
        context = {
            'default_move_type': 'out_invoice',
        }
        if len(self) == 1:
            context.update({
                'default_partner_id': self.partner_id.id,
                'default_invoice_origin': self.name,
            })
        action['context'] = context
        return action

    def action_create_invoice(self):
        """
        Triggers the invoice creation flow from the associated Sale Order.

        Delegates to sale_id.action_create_invoice() so that any override
        applied to that method (e.g. skip_invoice_wizard logic from
        sale_one_step_invoice) is automatically respected, without creating
        a hard dependency between modules.

        sudo() is used so that warehouse users without the Sales group can
        still trigger this action. The button visibility is already gated
        by the show_invoice_button compute field.
        """
        self.ensure_one()
        if not self.sudo().sale_id:
            return
        return self.sudo().sale_id.action_create_invoice()

    def button_validate(self):
        """
        Override to optionally trigger invoicing after validation.
        """
        # First, execute the standard validation
        res = super(Picking, self).button_validate()

        # If the validation returned an action (e.g., wizard, error), return it immediately
        # We only proceed if the validation was successful (usually returns True or None/False if done)
        if isinstance(res, dict):
            return res

        # Check if we should auto-invoice
        # We check self.sale_id to ensure there is a linked SO
        # We check if the picking is done (validation successful)
        for picking in self:
            if picking.state == 'done' and picking.sale_id and \
               picking.picking_type_id.auto_invoice and \
               picking.picking_type_id.auto_invoice_on_validate:
                
                # Trigger the invoice creation
                action = picking.action_create_invoice()
                
                # If the invoice creation returns an action (e.g. wizard or view), return it
                if action:
                    return action
        
        return res
