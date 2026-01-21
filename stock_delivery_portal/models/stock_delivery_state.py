from odoo import models, fields, api

class StockDeliveryState(models.Model):
    _name = 'stock.delivery.state'
    _description = 'Stock Delivery State'
    _order = 'sequence, id'
    _check_company_auto = True

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    
    help_delivery = fields.Text(string="Help for Drivers", help="Instructions shown to the driver in the portal")
    active = fields.Boolean(default=True)

    # Classification
    is_result_state = fields.Boolean(string="Is Result State", default=False)
    result_type = fields.Selection([
        ('success', 'Success'),
        ('partial', 'Partial Success'),
        ('failure', 'Failure')
    ], string="Result Type", required=False) # Programmatically required if is_result_state=True

    # Configuration
    picking_type_ids = fields.Many2many('stock.picking.type', string="Operation Types", check_company=True)
    
    # Automation
    mail_template_id = fields.Many2one('mail.template', string="Email Template", domain=[('model', '=', 'stock.picking')])
    
    # WhatsApp Template - Using string reference to avoid hard dependency if possible, 
    # but 'whatsapp' module is expected for this functionality.
    whatsapp_template_id = fields.Many2one('whatsapp.template', string="WhatsApp Template", domain=[('model', '=', 'stock.picking')])

    # Requirements
    require_signature = fields.Boolean(string="Require Signature")
    require_photo = fields.Boolean(string="Require Photo")
    require_receiver_name = fields.Boolean(string="Require Receiver Name")

    # Legal
    legal_text = fields.Text(string="Legal Text", translate=True, help="Legal text to display/accept during this state")

    @api.onchange('is_result_state')
    def _onchange_is_result_state(self):
        if not self.is_result_state:
            self.result_type = False
