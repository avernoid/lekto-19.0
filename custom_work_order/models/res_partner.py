from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    delivery_contact_name = fields.Char(
        string="Delivery Contact",
        help="Name of the person who picks up or receives the goods at this "
             "delivery address. It is printed in the 'Shipping Details' section "
             "(Part 3) of the Work Order report as the contact responsible for "
             "the delivery. Leave it empty if no specific contact applies; the "
             "report will then show only the phone number, or '-' if none.",
    )
