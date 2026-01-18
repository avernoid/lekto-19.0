from odoo import fields, models

class AccountJournal(models.Model):
    _inherit = "account.journal"

    cfi_round_qty_to_int = fields.Boolean(
        string="Round Quantity to Integer (Classic)",
        help="If checked, the quantity is printed without decimals.",
        default=False,
    )

    # Visual Configuration
    cfi_logo = fields.Binary(string='Classic Format Logo', help='Specific logo to be printed on this invoice format. If left empty, the standard Company Logo is used as fallback.')
    
    cfi_font_family = fields.Selection([
        ('Roboto', 'Roboto'),
        ('Montserrat', 'Montserrat'),
        ('Lato', 'Lato'),
        ('Oswald', 'Oswald'),
        ('Open Sans', 'Open Sans'),
        ('Courier New', 'Courier New'),
        ('Arial', 'Arial'),
        ('Verdana', 'Verdana'),
        ('Times New Roman', 'Times New Roman'),
    ], string='Font Family (Classic)', help='Select a custom font for the invoice to match your branding. If left empty, it uses the default font.')

    # Font Sizes
    cfi_company_name_size = fields.Integer(string='Company Name Size (Classic)', default=14, help='Font size in pixels (px) for the Company Name.')
    cfi_company_details_size = fields.Integer(string='Company Details Size (Classic)', default=14, help='Font size in pixels (px) for address/phone.')
    cfi_invoice_details_size = fields.Integer(string='Invoice Details Size (Classic)', default=14, help='Font size in pixels (px) for RUC, Document Name headers.')
    
    cfi_customer_details_size = fields.Integer(string='Customer Details Size (Classic)', default=11, help='Font size in pixels (px) for Customer data.')
    
    cfi_table_header_size = fields.Integer(string='Table Header Size (Classic)', default=12, help='Font size in pixels (px) for table headers.')
    cfi_table_body_size = fields.Integer(string='Table Body Size (Classic)', default=12, help='Font size in pixels (px) for table content.')
    
    cfi_totals_size = fields.Integer(string='Totals Size (Classic)', default=12, help='Font size in pixels (px) for totals area.')
    cfi_footer_msg_size = fields.Integer(string='Footer Message Size (Classic)', default=11, help='Font size in pixels (px) for terms and additional info.')

    # Modern Design Fields
    cfi_template = fields.Selection(
        selection=[
            ('classic', 'Classic (Official)'),
            ('modern', 'Modern (Professional)'),
        ],
        string="Invoice Design",
        default='classic',
        help="Select the design template for invoices printed from this journal."
    )
    cfi_primary_color = fields.Char(string="Primary Color", default="#00A09D", help="Hex code for the main thematic color (borders, icons).")
    cfi_show_qr = fields.Boolean(string="Show QR Code", default=True, help="Display the Electronic Invoice QR code (if available).")
    cfi_show_watermark = fields.Boolean(string="Show Status Watermark", default=True, help="Show DRAFT/PAID/CANCELLED watermark.")
    cfi_show_banks = fields.Boolean(string="Show Bank Accounts", default=True, help="Display structured bank accounts in the footer.")
    cfi_show_signature = fields.Boolean(string="Show Signature Area", default=False, help="Add a 'Received By' signature block.")
    cfi_show_product_images = fields.Boolean(string="Show Product Images", default=False)