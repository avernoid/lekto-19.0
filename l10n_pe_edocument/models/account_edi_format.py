from requests.exceptions import URLRequired
from zeep.wsse.username import UsernameToken
from zeep.exceptions import Fault
from odoo import _, api, models
import base64
from ..data.sunat_error_codes import SUNAT_ERROR_CODES
import logging

_logger = logging.getLogger(__name__)

class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    @api.model
    def _l10n_pe_edi_get_general_error_messages(self):
        """ Agrega mensajes de error dependiendo del codigo de error de SUNAT """
        res = super(AccountEdiFormat, self)._l10n_pe_edi_get_general_error_messages()
        res['L10NPE12'] = 'No se ha podido establecer la conexión.'
        return res

    def remove_existing_edi_attachments(self, invoice, edi_filename):
        """
        Elimina archivos adjuntos existentes con el mismo nombre de archivo EDI para evitar duplicados.
        """
        existing_attachments = self.env['ir.attachment'].search([
            ('res_model', '=', invoice._name),
            ('res_id', '=', invoice.id),
            ('name', '=', '%s.zip' % edi_filename)
        ])
        if existing_attachments:
            existing_attachments.unlink()

        existing_msg = self.env['mail.message'].search([
            ('model', '=', invoice._name),
            ('res_id', '=', invoice.id),
            ('body', '=', '<p>EL documento EDI tiene un formato incorrecto, revisar el .zip</p>')
        ])
        if existing_msg:
            _logger.info('l10n_pe_edocument: Removing existing attachment and message of the SUNAT xml error:  %s', invoice._name)
            existing_msg.unlink()

    def l10n_pe_edi_create_attachment_xml_error(self, invoice, edi_filename, xml_document_str):
        """ Genera un adjunto con extension zip con el archivo xml que no ha sido aceptado por SUNAT (por defecto no guarda este registro) """

        self.remove_existing_edi_attachments(invoice, edi_filename)

        zip_edi_str = self._l10n_pe_edi_zip_edi_document([('%s.xml' % edi_filename, xml_document_str)])
        attachment_id = self.env['ir.attachment'].create({
            'res_model': invoice._name,
            'res_id': invoice.id,
            'type': 'binary',
            'name': '%s.zip' % edi_filename,
            'datas': base64.encodebytes(zip_edi_str),
            'mimetype': 'application/zip'
        })
        message = _("EL documento EDI tiene un formato incorrecto, revisar el .zip")
        invoice.with_context(no_new_invoice=True).message_post(
            body=message,
            attachment_ids=[attachment_id.id],
        )

    @api.model
    def _l10n_pe_edi_get_cdr_error_messages(self):
        """
            Agrega mensajes de error faltantes dependiendo del codigo de error de SUNAT https://www.nubefact.com/codigos-error-sunat
        """
        error_codes_dict = super(AccountEdiFormat, self)._l10n_pe_edi_get_cdr_error_messages()
        error_codes_dict.update(SUNAT_ERROR_CODES)
        return error_codes_dict

    def _l10n_pe_edi_get_ose_credentials(self, company):
        """ Credenciales usadas por el proveedor OSE """
        self.ensure_one()
        res = {'fault_ns': 'soap-env'}
        if company.l10n_pe_edi_test_env:
            res.update({
                'wsdl': company.l10n_pe_edi_provider_ose_test_wsdl,
                'token': UsernameToken('{}MODDATOS'.format(company.vat), 'MODDATOS')
            })
        else:
            res.update({
                'wsdl': company.l10n_pe_edi_provider_ose_prod_wsdl,
                'token': UsernameToken(f'{company.vat}{company.sudo().l10n_pe_edi_provider_username}', company.sudo().l10n_pe_edi_provider_password)
            })
        return res

    def _l10n_pe_edi_sign_invoices_ose(self, invoice, edi_filename, edi_str):
        return self._l10n_pe_edi_sign_service_ose(invoice.company_id, edi_filename, edi_str, invoice.l10n_latam_document_type_id.code)

    def _l10n_pe_edi_sign_service_ose(self, company, edi_filename, edi_str, latam_document_type):
        credentials = self._l10n_pe_edi_get_ose_credentials(company)
        return self._l10n_pe_edi_sign_service_sunat_digiflow_common(
            company, edi_filename, edi_str, credentials, latam_document_type)

    def _l10n_pe_edi_cancel_invoices_step_1_ose(self, company, invoices, void_filename, void_str):
        credentials = self._l10n_pe_edi_get_ose_credentials(company)
        return self._l10n_pe_edi_cancel_invoices_step_1_sunat_digiflow_common(company, invoices, void_filename, void_str, credentials)

    def _l10n_pe_edi_cancel_invoices_step_2_ose(self, company, edi_values, cdr_number):
        credentials = self._l10n_pe_edi_get_ose_credentials(company)
        return self._l10n_pe_edi_cancel_invoices_step_2_sunat_digiflow_common(company, edi_values, cdr_number, credentials)

    def _l10n_pe_edi_get_status_cdr_ose_service(self, company, serie_folio, latam_document_type):
        credentials = self._l10n_pe_edi_get_ose_credentials(company)
        return self._l10n_pe_edi_get_status_cdr_sunat_digiflow_service_common(credentials, company.vat, serie_folio, latam_document_type)

    def _l10n_pe_edi_cancel_invoices_step_1_sunat_digiflow_common(self, company, invoices, void_filename, void_str, credentials):
        """
            El método result.raise_for_status() se esta extendiendo para que muestre mas informacion de la peticion y con ello se fuerza que el error HTTPError
            ahora sea un error URLRequired, el cual no es controlado el flujo nativo, por reso se agrega esta excepción
        """
        try:
            res = super(AccountEdiFormat, self)._l10n_pe_edi_cancel_invoices_step_1_sunat_digiflow_common(company, invoices, void_filename, void_str,
                                                                                                          credentials)
        except URLRequired as http_error:
            res = {'error': http_error, 'blocking_level': 'warning'}
        return res

    def _l10n_pe_edi_cancel_invoices_step_2_sunat_digiflow_common(self, company, edi_values, cdr_number, credentials):
        """
            El método result.raise_for_status() se esta extendiendo para que muestre mas informacion de la peticion y con ello se fuerza que el error HTTPError
            ahora sea un error URLRequired, el cual no es controlado el flujo nativo, por reso se agrega esta excepción
        """
        try:
            res = super(AccountEdiFormat, self)._l10n_pe_edi_cancel_invoices_step_2_sunat_digiflow_common(company, edi_values, cdr_number, credentials)
        except URLRequired as http_error:
            res = {'error': http_error, 'blocking_level': 'warning'}
        return res

    def _l10n_pe_edi_sign_service_sunat_digiflow_common(self, company, edi_filename, edi_str, credentials, latam_document_type):
        """
            El método result.raise_for_status() se esta extendiendo para que muestre mas informacion de la peticion y con ello se fuerza que el error HTTPError
            ahora sea un error URLRequired, el cual no es controlado el flujo nativo, por reso se agrega esta excepción
        """
        try:
            res = super(AccountEdiFormat, self)._l10n_pe_edi_sign_service_sunat_digiflow_common(company, edi_filename, edi_str, credentials,
                                                                                                latam_document_type)
        except Fault as sf:
            msj = sf.detail.find('message').text if sf.detail is not None else False
            res = {'error': msj if msj else sf.message, 'blocking_level': 'error'}
        except URLRequired as http_error:
            res = {'error': http_error, 'blocking_level': 'warning'}
        return res

    def _l10n_pe_edi_post_invoice_web_service(self, invoice, edi_filename, edi_str):
        res = super(AccountEdiFormat, self)._l10n_pe_edi_post_invoice_web_service(invoice, edi_filename, edi_str)
        if res.get('error'):
            self.l10n_pe_edi_create_attachment_xml_error(invoice, edi_filename, edi_str)
        return res
