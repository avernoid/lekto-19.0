from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from .apps import SunatPartner


class ActivityEconomicSunat(models.Model):
    _name = 'activity.economic.sunat'
    _description = 'Actividad(es) Económica(s) SUNAT'
    name = fields.Char(
        string='Name',
        required=True
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner'
    )


class DocumentPaySunat(models.Model):
    _name = 'document.pay.sunat'
    _description = 'Comprobantes de Pago c/aut. de impresión (F. 806 u 816) - SUNAT'

    name = fields.Char(
        string='Name',
        required=True
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner'
    )


class SystemElectronicSunat(models.Model):
    _name = 'system.electronic.sunat'
    _description = 'Sistema de Emision Electronica - SUNAT'

    name = fields.Char(
        string='Name',
        required=True
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner'
    )


class PatternSunat(models.Model):
    _name = 'pattern.sunat'
    _description = 'Padrones - SUNAT'

    name = fields.Char(
        string='Name',
        required=True
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner'
    )


class ResPartner(models.Model):
    _inherit = 'res.partner'

    document_type_sunat_id = fields.Many2one(
        comodel_name='l10n_latam.identification.type',
        string='SUNAT Document Type',
        help='Identification type according to SUNAT classification.'
    )
    # ... (rest of fields are unchanged, I will use context to skip them in replacement if possible, or just replace the header and footer) 

    # Since replace_file_content works better with contiguous blocks, and I need to change lines 63 and 221 which are far apart, 
    # I should strictly speaking use multi_replace_file_content or two replace calls. 
    # However, I can't see the full file content in the prompt to be sure about context lines for potential middle-file edits.
    # Wait, I CAN see the file content from step 800.
    # Line 63: _inherit = 'res.partner'
    # Line 221: arch, view = self._tags_invisible_per_country(arch, view, tags, [self.env.ref('base.pe')])
    
    # I will use multi_replace_file_content as it's cleaner for non-contiguous edits.
    pass

    document_type_sunat_id = fields.Many2one(
        comodel_name='l10n_latam.identification.type',
        string='SUNAT Document Type',
        help='Identification type used in SUNAT records.'
    )
    number_document_sunat = fields.Char(
        string='SUNAT Document Number',
        help='The unique number identifying the document in SUNAT.'
    )
    type_contributor_sunat = fields.Char(
        string='Contributor Type',
        help='Classification of the taxpayer (e.g., Natural Person, Legal Entity).'
    )
    type_document_sunat = fields.Char(
        string='Document Type',
        help='Type of identity document.'
    )
    date_inscription_sunat = fields.Date(
        string='Inscription Date',
        help='Date registered in SUNAT. If prior to 1900, it records as 01/01/1900.'
    )
    date_start_activity_sunat = fields.Date(
        string='Activity Start Date',
        help='Date when business activities commenced associated with this RUC.'
    )
    ple_date_sunat = fields.Date(
        string='Affiliated to PLE since',
        help='Date since the taxpayer is affiliated with the Electronic Books Program (PLE).'
    )
    emissor_date_sunat = fields.Date(
        string='Electronic Issuer since',
        help='Date since the taxpayer is authorized to issue electronic receipts.'
    )
    document_electronic_sunat = fields.Char(
        string='Electronic Receipts',
        help='Types of electronic receipts authorized for this taxpayer.'
    )
    state_contributor_sunat = fields.Char(
        string='Contributor State',
        help='Current status of the taxpayer (e.g., Active, Suspended).'
    )
    condition_contributor_sunat = fields.Char(
        string='Contributor Condition',
        help='Fiscal condition of the taxpayer (e.g., Habido, No Habido).'
    )
    office_sunat = fields.Char(
        string='Profession or Trade',
        help='Registered profession or trade of the taxpayer.'
    )
    system_emission_sunat = fields.Char(
        string='Emission System',
        help='System used for issuing receipts (e.g., Portal, OSE).'
    )
    system_account_sunat = fields.Char(
        string='Accounting System',
        help='Accounting system used (e.g., Manual, Computerized).'
    )
    foreign_activity_commerce_sunat = fields.Char(
        string='Foreign Trade Activity',
        help='Indicates if the taxpayer engages in import/export activities.'
    )
    activity_economic_ids = fields.One2many(
        comodel_name='activity.economic.sunat',
        inverse_name='partner_id',
        string='Economic Activities',
        help='List of economic activities registered.'
    )
    document_pay_ids = fields.One2many(
        comodel_name='document.pay.sunat',
        inverse_name='partner_id',
        string='Payment Vouchers (F. 806 or 816)',
        help='Authorized payment vouchers.'
    )
    system_electronic_ids = fields.One2many(
        comodel_name='system.electronic.sunat',
        inverse_name='partner_id',
        string='Electronic Emission System',
        help='Details of the electronic emission systems used.'
    )
    pattern_sunat_ids = fields.One2many(
        comodel_name='pattern.sunat',
        inverse_name='partner_id',
        string='Agreements/Patterns',
        help='Specific taxpayer patterns or agreements.'
    )

    pattern_sunat_ids = fields.One2many(
        comodel_name='pattern.sunat',
        inverse_name='partner_id',
        string='Agreements/Patterns',
        help='Specific taxpayer patterns or agreements.'
    )

    l10n_pe_vat_code = fields.Char(related='l10n_latam_identification_type_id.l10n_pe_vat_code')

    @api.onchange('vat', 'l10n_latam_identification_type_id')
    def _onchange_vat(self):
        if self.vat and not self.name:
            self.name = self.vat

    @api.model
    def handle_data_sunat(self, partner):
        vat = partner.get('vat')
        document_type = int(partner.get('l10n_latam_identification_type_id'))
        token_api = self.env.company.token_api_ruc
        values = {}
        if not token_api:
            raise UserError('No se agregó un token de consulta RUC en la compañía logeada actual.')
        if document_type and vat:
            document_type_code = self.env['l10n_latam.identification.type'].browse(document_type).l10n_pe_vat_code
            obj_sunat_yaros = SunatPartner(vat, document_type_code, token_api)
            values = obj_sunat_yaros.action_validate_api()

            if values and values.get('document_type_sunat_id'):
                obj_document_type_origin = self.env['l10n_latam.identification.type'].search([('l10n_pe_vat_code', '=', values['document_type_sunat_id'])],
                                                                                          limit=1)

                if values['document_type_sunat_id'] in ('1', '6'):
                    values.update({
                        'country_id': self.env.ref('base.pe').id,
                        'l10n_latam_identification_type_id': self.l10n_latam_identification_type_id.id,
                        'document_type_sunat_id': self.l10n_latam_identification_type_id.id
                    })
                else:
                    values.update({
                        'country_id': self.env.ref('base.pe').id,
                        'l10n_latam_identification_type_id': obj_document_type_origin.id,
                        'document_type_sunat_id': obj_document_type_origin.id
                    })
                if document_type_code == '6':
                    if values['state_id']:
                        state_id = self.env['res.country.state'].search([
                            ('code', '=', values['state_id']),
                            ('country_id', '=', self.env.ref('base.pe').id)], limit=1)
                        values['state_id'] = state_id.id if state_id else False
                    if values['city_id']:
                        city_id = self.env['res.city'].search([
                            ('l10n_pe_code', '=', values['city_id']),
                            ('country_id', '=', self.env.ref('base.pe').id)], limit=1)
                        values['city_id'] = city_id.id if city_id else False
                    if values['l10n_pe_district']:
                        l10n_pe_district = self.env['l10n_pe.res.city.district'].search([('code', '=', values['l10n_pe_district'])], limit=1)
                        values['l10n_pe_district'] = l10n_pe_district.id if l10n_pe_district else False
        if partner.get('id') and values:
            values['id'] = partner.get('id')
        return values

    @api.model
    def action_validate_sunat(self, partner):
        partner_id = partner.get('id')
        values = self.handle_data_sunat(partner)
        if values:
            if partner_id:
                obj_partner = self.browse(partner_id)
                obj_partner.activity_economic_ids.unlink()
                obj_partner.document_pay_ids.unlink()
                obj_partner.system_electronic_ids.unlink()
                obj_partner.pattern_sunat_ids.unlink()
                obj_partner.write(values)
            else:
                partner_id = self.create(values).id
        else:
            partner_id = False

        return partner_id

    def action_ruc_validation_sunat(self):
        self.ensure_one()
        values = {
            'vat': self.vat,
            'l10n_latam_identification_type_id': self.l10n_latam_identification_type_id.id,
            'id': self.id
        }
        if not self.action_validate_sunat(values):
            raise ValidationError(
                'No se puede realizar la consulta, porque el servicio de SUNAT está demorando en Responder, o su conexión a Internet es demasiado lenta. '
                'Pruebe haciendo la consulta manual directo en la página de consulta RUC de SUNAT, porque si el servicio de SUNAT presenta problemas de '
                'lentitud, Odoo no se conectará para evitar afectar el rendimiento del sistema.')
        return True




class ResCompany(models.Model):
    _inherit = 'res.company'

    token_api_ruc = fields.Char(string='RUC Query Token', help='API Token for querying RUC data from the service.')
