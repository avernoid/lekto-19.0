from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    quotation_payment_block = fields.Html(
        string="Payment Details (Quotation)",
        help="Free HTML block with the bank account details, withholdings "
             "and payment conditions printed in the 'Payment Details' section "
             "of the corporate quotation report. Leave it empty to hide the "
             "bank-account content (a placeholder note is shown on the report "
             "instead). The content is shared by every quotation of this "
             "company and can include tables, lists and styled text.",
        sanitize_style=True,
    )
    quotation_certification_logo = fields.Image(
        string="Certification Logo (Quotation)",
        help="Certification seal image (e.g. ISO 9001 / SGS / UKAS) shown next "
             "to the company logo in the header of the corporate quotation "
             "report. When empty, only the company logo is printed.",
    )
    quotation_footer_icon_phone = fields.Binary(
        string="Phone Icon (Footer)",
        help="SVG phone icon printed before the phone number in the footer of "
             "the corporate quotation report. When empty, the phone number is "
             "printed without an icon.",
    )
    quotation_footer_icon_email = fields.Binary(
        string="Email Icon (Footer)",
        help="SVG envelope/email icon printed before the email address in the "
             "footer of the corporate quotation report. When empty, the email "
             "is printed without an icon.",
    )
    quotation_document_code = fields.Char(
        string="Document Code (Quotation)",
        help="Optional document code printed in the top-right corner of the "
             "corporate quotation header (e.g. an internal form code such as "
             "'XX-YY-FT-000 Rev. 0'). When empty, no code is printed.",
    )
