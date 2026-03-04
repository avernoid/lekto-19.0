from odoo import models, fields


class TypeInputs(models.Model):
    _name = "type.inputs"
    _description = 'Work Day Type Inputs for Pay Slip Vouchers'

    name = fields.Char(
        string='Name',
        help=(
            "Display name for this work day type input. "
            "Used to identify the category in reports and configuration views."
        )
    )
    code = fields.Char(
        string='Code',
        help=(
            "Technical code used by the payroll engine to classify worked-day entries on the pay slip voucher. "
            "Supported codes: 'work' (regular days), 'holidays' (vacation/holiday days), 'break' (rest/break days), "
            "'sanctioned' (disciplinary days), 'not_working' (non-working subsidy days), "
            "'subsidies' (subsidy days), 'medical_rest' (medical leave days). "
            "Each code maps to a specific column in the day summary section of the voucher."
        )
    )
    description = fields.Char(
        string='Description',
        help=(
            "Optional human-readable description explaining what this type of worked day represents. "
            "Useful for internal documentation and HR configuration."
        )
    )
