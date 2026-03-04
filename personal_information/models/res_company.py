from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    generate_legal_name = fields.Boolean(
        string='Auto-generate Legal Name',
        default=True,
        help=(
            'If enabled, the "Legal Name" field of the employee will be automatically '
            'updated whenever "First Name", "Paternal Lastname" or "Maternal Lastname" '
            'are modified. The result is the concatenation: First Name + Paternal Lastname '
            '+ Maternal Lastname.'
        )
    )
    generate_employee_name = fields.Boolean(
        string='Auto-generate Employee Name',
        default=False,
        help=(
            'If enabled, the "Name" field of the employee will be automatically '
            'updated whenever "First Name", "Paternal Lastname" or "Maternal Lastname" '
            'are modified. The result is the concatenation: First Name + Paternal Lastname '
            '+ Maternal Lastname.'
        )
    )
