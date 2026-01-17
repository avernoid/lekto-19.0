
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re


class ResPartner(models.Model):
    _inherit = 'res.partner'

    error_dialog = fields.Text(
        compute='_compute_error_dialog_partner',
        store=False,
        help='Campo usado para mostrar mensaje de alerta en el mismo formulario'
    )

    @api.model
    def _validate_length_vat(self, vat, doc_length, exact_length):
        if exact_length == 'exact':
            if len(vat) != doc_length:
                return _('- The number of characters for the identification number must be: {doc_length}.\n').format(doc_length=doc_length)

        elif exact_length == 'maximum':
            if len(vat) > doc_length:
                return _('- The number of characters for the identification number must be at most: {doc_length}.\n').format(doc_length=doc_length)

        return ''

    @api.model
    def _validate_structure_vat(self, vat, doc_type, validation_regex):
        # 1. Regex Validation (Priority)
        if validation_regex:
            if not re.match(validation_regex, vat):
                return _('- The identification number does not follow the expected pattern.\n')
            return ''

        # 2. Standard Validation (Fallback)
        if doc_type == 'other':
            return ''

        elif doc_type == 'numeric':
            if not vat.isdigit():
                return _('- The identification number must contain only numbers.\n')
            
            # Check if it contains only zeros
            if all(c == '0' for c in vat):
                return _('- The identification number cannot contain only zeros.\n')

        elif doc_type == 'alphanumeric':
            # Check for special characters using regex
            # Provide a set of allowed characters or disallowed characters.
            # The original code acted as a blacklist. Let's maintain that behavior but cleaner.
            regex = r'[-°%&=~\\+?*^$()\[\]{}|@%#"/¡¿!:.,;]'
            if re.search(regex, vat):
                return _('- The identification number contains not allowed characters.\n')

        return ''

    @api.depends('l10n_latam_identification_type_id', 'vat')
    def _compute_error_dialog_partner(self):
        for partner in self:
            error_dialog = ''
            if partner.l10n_latam_identification_type_id and partner.vat:
                error_dialog += self._validate_length_vat(
                    partner.vat,
                    partner.l10n_latam_identification_type_id.doc_length,
                    partner.l10n_latam_identification_type_id.exact_length
                )
                error_dialog += self._validate_structure_vat(
                    partner.vat,
                    partner.l10n_latam_identification_type_id.doc_type,
                    partner.l10n_latam_identification_type_id.validation_regex
                )
            partner.error_dialog = error_dialog

    @api.constrains('l10n_latam_identification_type_id', 'vat')
    def _check_doc_type_validation(self):
        for partner in self:
            if partner.error_dialog:
                raise ValidationError(partner.error_dialog)
