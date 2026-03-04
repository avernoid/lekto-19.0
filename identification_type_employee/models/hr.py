from odoo import api, fields, models


def _validate_long(word, length, validation_type, field_name):
    if word and validation_type:
        if validation_type == 'exact':
            if len(word) != length:
                return "- La cantidad de caracteres para el campo '%s' debe ser: %d \n" % \
                       (field_name, length)
        elif validation_type == 'maximum':
            if len(word) > length:
                return "- La cantidad de caracteres para el campo '%s' debe ser como máximo: %d \n" % \
                       (field_name, length)
    return ''


def _validate_word_structure(word, validation_type, field_name):
    special_characters = '-°%&=~\\+?*^$()[]{}|@%#"/¡¿!:.,;'
    if word:
        if validation_type == 'other':
            return ''
        if validation_type == 'numeric':
            if not word.isdigit():
                return "- El campo '%s' solo debe contener números.\n" % field_name
            else:
                total = 0
                for d in str(word):
                    total += int(d)
                if total == 0:
                    return "- El campo '%s' no puede contener solo ceros.\n" % field_name
        special = ''
        for letter in word:
            if letter in special_characters:
                special += letter
        if special != '':
            return "- El campo '%s' contiene caracteres no permitidos:  %s \n" % (field_name, special)
    return ''


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    type_identification_id = fields.Many2one(
        comodel_name="l10n_latam.identification.type",
        string='Employee Document Type',
        groups="hr.group_hr_user",
        help="Select the specific type of identification document for this employee (e.g., National ID, Passport, Driver's License). This field categorizes the identification number properly according to localization standards.",
    )
    document_country_id = fields.Many2one(
        comodel_name="res.country",
        string='Issuing Country',
        groups="hr.group_hr_user",
        help="Specifies the country that issued the document. This field dynamicly appears only when an international or foreign document type is selected.",
    )
    error_dialog = fields.Text(
        compute="_compute_error_dialog_partner",
        store=True,
        help="Technical field used to display real-time validation error alerts on the form view when the document number does not match the rules of the selected document type.",
        groups="hr.group_hr_user"
    )
    doc_nationality = fields.Selection(
        selection=[
            ('national', 'National'),
            ('foreign', 'Foreign'),
            ('both', 'Both')],
        string='Document Nationality',
        compute='_compute_doc_nationality',
        groups="hr.group_hr_user",
        store=True,
        help="Technical field that auto-computes the target nationality (National, Foreign, Both) based on the selected document type. Used to dynamically show or hide the Issuing Country field.",
    )

    @api.depends('type_identification_id')
    def _compute_doc_nationality(self):
        for rec in self:
            if rec.type_identification_id and rec.type_identification_id.nationality:
                rec.doc_nationality = rec.type_identification_id.nationality

    @api.depends('country_id', 'type_identification_id', 'identification_id')
    def _compute_error_dialog_partner(self):
        for rec in self:
            msg = ''
            if rec.type_identification_id:
                if rec.identification_id:
                    type_document_partner = rec.type_identification_id.exact_length
                    msg += _validate_long(rec.identification_id, rec.type_identification_id.doc_length, type_document_partner, 'Número Documento')
                    msg += _validate_word_structure(rec.identification_id, rec.type_identification_id.doc_type, 'Número Documento')
            rec.error_dialog = msg

    @api.onchange('identification_id', 'error_dialog')
    def _onchange_error_dialog_employee(self):
        for rec in self:
            if rec.error_dialog:
                error = rec.error_dialog
                rec.identification_id = False
                rec.error_dialog = error
