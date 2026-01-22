from odoo import models, fields, api

class StockDeliveryState(models.Model):
    _name = 'stock.delivery.state'
    _description = 'Stock Delivery State'
    _order = 'sequence, id'
    _check_company_auto = True

    name = fields.Char(required=True, translate=True, help="Name of the delivery state (e.g. Delivered, On the way).")
    sequence = fields.Integer(default=10, help="Sequence for sorting states in the list.")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company, help="Company this state belongs to.")
    icon = fields.Char(string="Font Awesome Icon", help="Font Awesome icon class (e.g. fa-truck, fa-check, fa-upload). Do not include 'fa' prefix, only the icon name (e.g. 'fa-truck').")
    
    help_delivery = fields.Text(string="Help for Drivers", help="Instructions shown to the driver in the portal during this state.")
    active = fields.Boolean(default=True, help="If unchecked, it will allow you to hide the state without removing it.")

    # Classification
    is_result_state = fields.Boolean(string="Is Result State", default=False, help="Check this if this state represents a final outcome (e.g. Delivered, Failed).")
    result_type = fields.Selection([
        ('success', 'Success'),
        ('partial', 'Partial Success'),
        ('failure', 'Failure')
    ], string="Result Type", required=False, help="Classification of the result: Success, Partial or Failure.") # Programmatically required if is_result_state=True

    # Configuration
    picking_type_ids = fields.Many2many('stock.picking.type', string="Operation Types", check_company=True, help="Operation types where this state can be used.")
    
    # Automation
    mail_template_id = fields.Many2one('mail.template', string="Email Template", domain=[('model', '=', 'stock.picking')], help="Email template to send automatically when entering this state.")
    
    # WhatsApp Template - Using string reference to avoid hard dependency if possible, 
    # but 'whatsapp' module is expected for this functionality.
    whatsapp_template_id = fields.Many2one('whatsapp.template', string="WhatsApp Template", domain=[('model', '=', 'stock.picking')], help="WhatsApp template to send automatically when entering this state.")

    # Requirements (Visibility)
    require_signature = fields.Boolean(string="Require Signature", help="If true, the driver must provide a signature to switch to this state.")
    require_photo = fields.Boolean(string="Require Photo", help="If true, the driver must provide at least one photo to switch to this state.")
    require_receiver_name = fields.Boolean(string="Require Receiver Name", help="If true, the driver must provide the receiver's name.")

    # Requirements (Validation)
    is_signature_mandatory = fields.Boolean(string="Signature Mandatory", help="If checked, the user CANNOT submit without a signature.")
    is_photo_mandatory = fields.Boolean(string="Photo Mandatory", help="If checked, the user CANNOT submit without a photo.")
    is_receiver_name_mandatory = fields.Boolean(string="Receiver Name Mandatory", help="If checked, the user CANNOT submit without a receiver name.")

    # Legal
    legal_text = fields.Text(string="Legal Text", translate=True, help="Legal text to display/accept during this state")

    @api.onchange('is_result_state')
    def _onchange_is_result_state(self):
        if not self.is_result_state:
            self.result_type = False
