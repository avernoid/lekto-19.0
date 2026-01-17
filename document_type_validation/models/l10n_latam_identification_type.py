from odoo import fields, models


class L10nLatamIdentificationType(models.Model):
    _inherit = 'l10n_latam.identification.type'

    doc_length = fields.Integer(
        string='Length',
        help='Specifies the required length of the identification number.'
    )
    doc_type = fields.Selection(
        selection=[
            ('numeric', 'Numeric'),
            ('alphanumeric', 'Alphanumeric'),
            ('other', 'Other')],
        string='Type',
        help='Specifies whether the identification number must be numeric, alphanumeric, or other.'
    )
    exact_length = fields.Selection(
        selection=[
            ('exact', 'Exact'),
            ('maximum', 'Maximum')],
        string='Exact Length',
        help='Determines if the length check is exact or a maximum limit.'
    )
    nationality = fields.Selection(
        selection=[
            ('national', 'National'),
            ('foreign', 'Foreign'),
            ('both', 'Both')],
        string='Nationality',
        help='Indicates if this document type is for nationals, foreigners, or both.'
    )
    validation_regex = fields.Char(
        string='Validation Regex',
        help='Custom Regular Expression for advanced validation. If set, this regex takes precedence over the standard check.\n'
             'Example: ^[A-Z]{3}-[0-9]{3}$ will allow "ABC-123" but fail "123-ABC".'
    )
