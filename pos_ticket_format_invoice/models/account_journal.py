from odoo import api, fields, models

class AccountJounal(models.Model):
    _inherit = 'account.journal'

    address_point_emission = fields.Char(string='Point of Emission Address', help='Physical address printed on the ticket for this specific Point of Sale/Journal. It overrides the Company Address. If left empty, the generic Company Address is used.')
    
    # Visual Configuration
    ticket_logo = fields.Binary(string='Ticket Logo', help='Specific logo to be printed on this ticket (e.g., Black & White version for better contrast). If left empty, the standard Company Logo is used as fallback.')
    ticket_layout = fields.Selection([
        ('classic', 'Classic'),
        ('modern', 'Modern Invoice'),
        ('full_width', 'Full Width (Description on new line)'),
    ], string='Ticket Layout', default='classic', required=True, 
       help='Defines the visual structure of the printed ticket:\n'
            '- Classic: Standard compact layout with dashed separators.\n'
            '- Modern Invoice: Minimalist, high-contrast design (Black/White headers) with boxed totals.\n'
            '- Full Width: Optimized for long product names; places the description on its own line followed by values.')

    # Ticket Configuration
    ticket_font_family = fields.Selection([
        ('Roboto', 'Roboto'),
        ('Montserrat', 'Montserrat'),
        ('Lato', 'Lato'),
        ('Oswald', 'Oswald'),
        ('Open Sans', 'Open Sans'),
        ('Courier New', 'Courier New'),
        ('Arial', 'Arial'),
        ('Verdana', 'Verdana'),
        ('Times New Roman', 'Times New Roman'),
    ], string='Font Family', help='Select a custom font for the ticket to match your branding. If left empty, it uses the printer default font (inherit).')

    # Header Section
    ticket_company_name_size = fields.Integer(string='Company Name Size', default=12, help='Font size in pixels (px) for the Company Name at the top. Increase/Decrease to fit your paper width.')
    ticket_company_details_size = fields.Integer(string='Company Details Size', default=11, help='Font size in pixels (px) for the Company Address, Phone, and Email lines.')
    ticket_invoice_details_size = fields.Integer(string='Invoice Details Size', default=11, help='Font size in pixels (px) for the Invoice Number, Date, and Issuer lines.')

    # Table Content
    ticket_table_header_size = fields.Integer(string='Table Header Size', default=11, help='Font size in pixels (px) for the product table column titles (Qty, Description, Price, Total).')
    ticket_table_body_size = fields.Integer(string='Table Body Size', default=11, help='Font size in pixels (px) for the actual product lines (name, quantity, price).')

    # Customer Section
    ticket_customer_details_size = fields.Integer(string='Customer Details Size', default=11, help='Font size in pixels (px) for the Customer Name, VAT, and Contact info block.')

    # Totals & Footer
    ticket_totals_size = fields.Integer(string='Totals Size', default=11, help='Font size in pixels (px) for the Subtotal, Tax, and Grand Total block.')
    ticket_amount_text_size = fields.Integer(string='Amount in Words Size', default=11, help='Font size in pixels (px) for the "Amount in Words" text (Son...).')
    ticket_footer_msg_size = fields.Integer(string='Footer Message Size', default=11, help='Font size in pixels (px) for the Terms & Conditions (Narration) and Company Additional Info at the bottom.')
