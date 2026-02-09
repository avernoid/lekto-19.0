import base64
import hashlib
import requests
import urllib.parse

from lxml import etree
from lxml import objectify
from hashlib import sha1
from datetime import datetime
from copy import deepcopy
from pytz import timezone
from json.decoder import JSONDecodeError
from markupsafe import Markup

from odoo import api, models, fields, _, _lt
from odoo.exceptions import UserError

DEFAULT_PE_DATE_FORMAT = '%Y-%m-%d'

PE_TRANSFER_REASONS = [
    ('01', 'Sale'),
    ('02', 'Compra'),
    ('03', 'Sale with delivery to third parties'),
    ('04', 'Transfer between establishments of the same company'),
    ('05', 'Consignment'),
    ('06', 'Devolución'),
    ('07', 'Recojo de bienes transformados'),
    ('08', 'Importación'),
    ('09', 'Exportación'),
    ('13', 'Others'),
    ('14', "Sale subject to buyer's confirmation"),
    ('17', 'Transfer of goods for transformation'),
    ('18', 'Itinerant issuer transfer CP'),
    ('19', 'Transfer to primary zone (deprecated)'),  # TODO master: remove
]
PE_RELATED_DOCUMENT = [
    ('01', 'Factura'),
    ('03', 'Boleta de Venta'),
    ('04', 'Liquidación de Compra'),
    ('09', 'Guía de Remisión Remitente'),
    ('12', 'Ticket o cinta emitido por máquina registradora'),
    ('31', 'Guía de Remisión Transportista'),
    ('48', 'Comprobante de Operaciones - Ley N° 29972'),
    ('49', 'Constancia de Depósito - IVAP (Ley 28211)'),
    ('50', 'Declaración Aduanera de Mercancías'),
    ('52', 'Declaración Simplificada (DS)'),
    ('65', 'Autorización de Circulación para transportar MATPEL - Callao'),
    ('66', 'Autorización de Circulación para transporte de carga y mercancías en Lima Metropolitana'),
    ('67', 'Permiso de Operación Especial para el servicio de transporte de MATPEL - MTC'),
    ('68', 'Habilitación Sanitaria de Transporte Terrestre de Productos Pesqueros y Acuícolas'),
    ('69', 'Permiso / Autorización de operación de transporte de mercancías'),
    ('71', 'Resolución de Adjudicación de bienes - SUNAT'),
    ('72', 'Resolución de Comiso de bienes - SUNAT'),
    ('73', 'Guía de Transporte Forestal o de Fauna - SERFOR'),
    ('74', 'Guía de Tránsito - SUCAMEC'),
    ('75', 'Autorización para operar como empresa de Saneamiento Ambiental - MINSA'),
    ('76', 'Autorización para manejo y recojo de residuos sólidos peligrosos y no peligrosos'),
    ('77', 'Certificado fitosanitario la movilización de plantas, productos vegetales, y otros artículos reglamentados'),
    ('78', 'Registro Único de Usuarios y Transportistas de Alcohol Etílico'),
    ('80', 'Constancia de Depósito - Detracción'),
    ('81', 'Código de autorización emitida por el SCOP'),
    ('82', 'Declaración jurada de mudanza'),
]
ERROR_MESSAGES = {
    "request": _lt("There was an error communicating with the SUNAT service. Details:"),
    "json_decode": _lt("Could not decode the response received from SUNAT. Details:"),
    "unzip": _lt("Could not decompress the ZIP file received from SUNAT."),
    "processing": _lt("The delivery guide is being processed by SUNAT. Click on 'Retry' to refresh the state."),
    "processing_98": _lt("The delivery guide is being processed by SUNAT, Response code: 98. Click on 'Retry' to refresh the state."),
    "duplicate": _lt("A delivery guide with this number is already registered with SUNAT. Click on 'Retry' to try sending with a new number."),
    "response_code": _lt("SUNAT returned an error code. Details:"),
    "response_unknown": _lt("Could not identify content in the response retrieved from SUNAT. Details:"),
}


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    sunat_sequence = fields.Selection(
        selection='get_prefix',
        string='Electronic Guide Sequence',
        help='Sequence used for the Electronic Delivery Note (Guía de Remisión Remitente).',
    )

    l10n_pe_edi_reason_for_transfer = fields.Selection(
        selection_add=[
            ('02', 'Compra'),
            ('06', 'Devolución'),
            ('07', 'Recojo de bienes transformados'),
            ('08', 'Importación'),
            ('09', 'Exportación')
        ]
    )
    l10n_pe_edi_handling_instructions = fields.Char(
        string='Transfer Reason Description',
        help='Additional description when the reason for transfer is "Others".',
    )
    l10n_pe_edi_scheduled_transfer = fields.Boolean(
        string='Scheduled Transfer Indicator',
        help='Indicates if the transfer involves a scheduled transshipment.',
    )





    @api.onchange('l10n_pe_edi_reason_for_transfer')
    def _onchange_l10n_pe_edi_reason_for_transfer(self):
        if not self.l10n_pe_edi_reason_for_transfer == '13':
            self.l10n_pe_edi_handling_instructions = False

    def get_prefix(self):
        return [(key, key) for key in self.env['ir.sequence'].search([('code', '=', 'l10n_pe_edi_stock.stock_picking_sunat_sequence'),
                                                                      ('company_id.id', '=', self.env.company.id)]).mapped('prefix')]

    def _l10n_pe_sign(self, certificate, edi_tree):
        namespaces = {'ds': 'http://www.w3.org/2000/09/xmldsig#'}

        edi_tree_copy = deepcopy(edi_tree)
        signature_element = edi_tree_copy.xpath('.//ds:Signature', namespaces=namespaces)[0]
        signature_element.getparent().remove(signature_element)

        edi_tree_c14n_str = etree.tostring(edi_tree_copy, method='c14n', exclusive=True, with_comments=False)
        digest_b64 = base64.b64encode(sha1(edi_tree_c14n_str).digest())
        signature_str = self.env['ir.qweb']._render(
            'l10n_pe_edi.ubl_pe_21_signature_template',
            {'digest_value': digest_b64.decode()}
        )

        # Eliminate all non useful spaces and new lines in the stream
        signature_str = signature_str.replace('\n', '').replace('  ', '')

        signature_tree = etree.fromstring(signature_str)
        signed_info_element = signature_tree.xpath('.//ds:SignedInfo', namespaces=namespaces)[0]
        signature = etree.tostring(signed_info_element, method='c14n', exclusive=True, with_comments=False)
        signature_b64_hash = certificate._sign(signature, hashing_algorithm='sha1', formatting='base64')

        signature_tree.xpath('.//ds:SignatureValue', namespaces=namespaces)[0].text = signature_b64_hash
        signature_tree.xpath('.//ds:X509Certificate', namespaces=namespaces)[0].text = certificate._get_der_certificate_bytes(formatting='base64')
        signed_edi_tree = deepcopy(edi_tree)
        signature_element = signed_edi_tree.xpath('.//ds:Signature', namespaces=namespaces)[0]
        for child_element in signature_tree:
            signature_element.append(child_element)
        return signed_edi_tree
    
    def action_send_delivery_guide(self):
        """Check required fields, generate the XML delivery guide, and send it to SUNAT"""
        self._check_company()
        self._l10n_pe_edi_check_required_data()
        for record in self:
            # TODO: START OVERWRIDE
            if not record.sunat_sequence:
                raise UserError(
                    'Debe asignar una serie a su guía electrónica. '
                )

            if record.picking_type_id.code in ['internal', 'incoming']:
                if not record.location_dest_id.direction_id:
                    raise UserError(
                        'No se enviará la GRE hasta que no se configure el campo “dirección” dentro de la ubicación de stock. Debe colocar la dirección del almacén para que pueda enviar la GRE.'
                    )
            if record.picking_type_id.code in ['internal', 'outgoing']:
                if not record.location_id.direction_id:
                    raise UserError(
                        'No se enviará la GRE hasta que no se configure el campo “dirección” dentro de la ubicación de stock. Debe colocar la dirección del almacén para que pueda enviar la GRE.'
                    )
            # == Generate a document number ==
            if not record.l10n_latam_document_number:
                sunat_sequence = self.env['ir.sequence'].search([
                    ('code', '=', 'l10n_pe_edi_stock.stock_picking_sunat_sequence'),
                    ('prefix', '=', record.sunat_sequence),
                    ('company_id', '=', record.company_id.id)], limit=1)
                if not sunat_sequence:
                    sunat_sequence = self.env['ir.sequence'].sudo().create({
                        'name': 'Stock Picking Sunat Sequence %s' % record.company_id.name,
                        'code': 'l10n_pe_edi_stock.stock_picking_sunat_sequence',
                        'padding': 8,
                        'company_id': record.company_id.id,
                        'prefix': 'T001-',
                        'number_next': 1,
                    })
                record.l10n_latam_document_number = sunat_sequence.next_by_id()
            # TODO: END OVERWRIDE
            # == Send the delivery guide ==
            record.l10n_pe_edi_status = 'to_send'
            edi_str = record._l10n_pe_edi_create_delivery_guide()

            # TODO: START OVERWRIDE
            # if record.company_id.l10n_pe_edi_delivery_test_env:
            edi_tree = objectify.fromstring(edi_str)
            edi_tree = self._l10n_pe_sign(record.company_id.sudo().l10n_pe_edi_certificate_id, edi_tree)
            edi_str = etree.tostring(edi_tree, xml_declaration=True, encoding='ISO-8859-1')

            # TODO: END OVERWRIDE

            res = record._l10n_pe_edi_sign(edi_str)

            # TODO: START OVERWRIDE
            # == Create the attachments with error ==
            if 'error' in res:
                if res.get("error_reason") != "processing":
                    edi_filename = '%s-09-%s.xml' % (record.company_id.vat, record.l10n_latam_document_number)
                    zip_edi_str = self.env['account.edi.format']._l10n_pe_edi_zip_edi_document([('%s.xml' % edi_filename, edi_str)])
                    attachment_id = self.env['ir.attachment'].create({
                        'res_model': record._name,
                        'res_id': record.id,
                        'type': 'binary',
                        'name': '%s.zip' % edi_filename,
                        'datas': base64.encodebytes(zip_edi_str),
                        'mimetype': 'application/zip'
                    })
                    message = _("El documento EDI tiene un formato incorrecto, revisar el ZIP")
                    record.with_context(no_new_invoice=True).message_post(
                        body=message,
                        attachment_ids=[attachment_id.id],
                    )
                record.l10n_pe_edi_error = res['error']
                continue
            # TODO: END OVERWRIDE

            # == Create the attachments ==
            if res.get('cdr'):
                attachments = self.env['ir.attachment'].create([
                    {
                        'name': '%s-09-%s.xml' % (record.company_id.vat, record.l10n_latam_document_number),
                        'res_model': record._name,
                        'res_id': record.id,
                        'type': 'binary',
                        'raw': edi_str,
                        'mimetype': 'application/xml',
                        'description': _('Delivery Guide for transfer %s', record.name),
                    },
                    {
                        'name': 'cdr-%s-09-%s.xml' % (record.company_id.vat, record.l10n_latam_document_number),
                        'res_model': record._name,
                        'res_id': record.id,
                        'type': 'binary',
                        'raw': res['cdr'],
                        'mimetype': 'application/xml',
                        'description': _('Delivery guide receipt (CDR) for transfer %s', record.name)
                    }
                ])
                message = _("The Delivery Guide was successfully signed by SUNAT.")
                record._message_log(body=message, attachment_ids=attachments.ids)
                record.write({'l10n_pe_edi_error': False, 'l10n_pe_edi_status': 'sent'})

    def _l10n_pe_edi_get_delivery_guide_values(self):
        """ Used to generate the XML file that will be send to stamp in SUNAT
        The document number comes from the sequence with code "l10n_pe_edi_stock.stock_picking_sunat_sequence", and
        will be generated automatically if this not exists."""
        self.ensure_one()

        def format_date(date):
            return date.strftime(DEFAULT_PE_DATE_FORMAT) if date else ''

        def format_float(val, digits=2):
            return '%.*f' % (digits, val)

        date_pe = datetime.now(tz=timezone('America/Lima')).date()
        return {
            'date_issue': date_pe.strftime(DEFAULT_PE_DATE_FORMAT),
            'time_issue': date_pe.strftime("%H:%M:%S"),
            'l10n_pe_edi_observation': self.l10n_pe_edi_observation or 'Guía',
            'record': self,
            'weight_uom': self.env['product.template']._get_weight_uom_id_from_ir_config_parameter(),
            'warehouse_address': self.picking_type_id.warehouse_id.partner_id or self.company_id.partner_id,
            'document_number': self.l10n_latam_document_number,
            'format_date': format_date,
            'moves': self.move_ids.filtered(lambda ml: ml.quantity > 0),
            'reason_for_transfer': dict(PE_TRANSFER_REASONS)[self.l10n_pe_edi_reason_for_transfer] if not self.l10n_pe_edi_handling_instructions else self.l10n_pe_edi_handling_instructions,
            'format_float': format_float,
            'related_document': dict(PE_RELATED_DOCUMENT)[self.l10n_pe_edi_related_document_type] if self.l10n_pe_edi_related_document_type else False,
        }

    def _l10n_pe_edi_get_sunat_guia_credentials(self):
        company = self.company_id.sudo()
        if company.l10n_pe_edi_delivery_test_env:
            return {
                "access_id": "test-85e5b0ae-255c-4891-a595-0b98c65c9854",
                "access_key": "test-Hty/M6QshYvPgItX2P0+Kw==",
                "client_id": "{}MODDATOS".format(company.vat),
                "password": "MODDATOS",
                "login_url": "https://gre-test.nubefact.com/v1/clientessol/%s/oauth2/token/",
            }
        else:
            return super()._l10n_pe_edi_get_sunat_guia_credentials()

    def _l10n_pe_edi_send_delivery_guide(self, edi_str, token):
        """ Send a delivery guide to SUNAT via the REST API.

            SUNAT provides a ticket number in its response, which can be used to
            retrieve the CDR once the SUNAT service has finished processing the
            delivery guide.

            :param edi_str: the content of the XML file containing the delivery guide
            :param token: the SUNAT authentication token """
        self.ensure_one()
        headers = {
            'Authorization': "Bearer " + token,
            'Content-Type': "Application/json",
        }
        edi_filename = "%s-09-%s" % (self.company_id.vat, self.l10n_latam_document_number)
        url = "https://api-cpe.sunat.gob.pe/v1/contribuyente/gem/comprobantes/%s" % urllib.parse.quote_plus(edi_filename)
        # TODO: START OVERWRIDE
        if self.company_id.l10n_pe_edi_delivery_test_env:
            url = "https://gre-test.nubefact.com/v1/contribuyente/gem/comprobantes/%s" % urllib.parse.quote_plus(edi_filename)
        # TODO: END OVERWRIDE

        # SUNAT expects the XML to be encoded using ISO-8859-1.
        edi_str = etree.tostring(etree.fromstring(edi_str), xml_declaration=True, encoding='ISO-8859-1')
        zip_file = self.env.ref('l10n_pe_edi.edi_pe_ubl_2_1')._l10n_pe_edi_zip_edi_document([('%s.xml' % edi_filename, edi_str)])
        data = {
            "archivo": {
                "nomArchivo": "%s.zip" % edi_filename,
                "arcGreZip": base64.b64encode(zip_file).decode(),
                "hashZip": hashlib.sha256(zip_file).hexdigest(),
            }
        }
        try:
            response = requests.post(url, json=data, headers=headers, verify=True, timeout=20)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            to_return = {"error": str(Markup("%s<br/>%s") % (ERROR_MESSAGES["request"], e))}
            if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 401:
                to_return.update({"error_reason": "unauthorized"})
            return to_return
        try:
            response_json = response.json()
        except JSONDecodeError as e:
            return {"error": str(Markup("%s<br/>%s") % (ERROR_MESSAGES["json_decode"], e))}

        if isinstance(response_json.get("errors"), list) and len(response_json["errors"]) > 0 and isinstance(response_json["errors"][0], dict):
            code = response_json["errors"][0].get("cod", "")
            msg = response_json["errors"][0].get("msg", "")
            return {"error": str(Markup("%s<br/>%s: %s") % (ERROR_MESSAGES["response_code"], code, msg))}
        if not response_json.get("numTicket"):
            return {"error": str(Markup("%s<br/>%s") % (ERROR_MESSAGES["response_unknown"], response_json))}

        return {"ticket_number": response_json["numTicket"]}

    def _l10n_pe_edi_get_cdr(self, ticket_number, token):
        """ Retrieve the CDR (confirmation of receipt) for a delivery guide that was sent.

            :param ticket_number: the ticket number obtained when sending the delivery guide
            :param token: the SUNAT authentication token """
        headers = {
            'Authorization': "Bearer " + token,
            'Content-Type': "Application/json",
        }
        url = 'https://api-cpe.sunat.gob.pe/v1/contribuyente/gem/comprobantes/envios/%s' % urllib.parse.quote_plus(ticket_number)
        # TODO: START OVERWRIDE
        if self.company_id.l10n_pe_edi_delivery_test_env:
            url = 'https://gre-test.nubefact.com/v1/contribuyente/gem/comprobantes/envios/%s' % urllib.parse.quote(ticket_number)
        # TODO: END OVERWRIDE
        try:
            response = requests.get(url, params={'numTicket': ticket_number}, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            to_return = {"error": str(Markup("%s<br/>%s") % (ERROR_MESSAGES["request"], e))}
            if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 401:
                to_return.update({"error_reason": "unauthorized"})
            return to_return
        try:
            response_json = response.json()
        except JSONDecodeError as e:
            return {"error": str(Markup("%s<br/>%s") % (ERROR_MESSAGES["json_decode"], e))}

        if response_json.get("codRespuesta") == "98":
            error_msg = ERROR_MESSAGES["processing_98"]
            return {"error": error_msg, "error_reason": "processing"}
        if response_json.get("error"):
            code = response_json["error"].get("numError", "")
            msg = response_json["error"].get("desError", "")
            if code == "1033":
                error_msg = ERROR_MESSAGES["duplicate"]
                return {"error": error_msg, "error_reason": "duplicate"}
            else:
                return {"error": str(Markup("%s %s: %s") % (ERROR_MESSAGES["response_code"], code, msg)), "error_reason": "rejected"}
        if not response_json.get("arcCdr") or response_json.get("codRespuesta") != "0":
            if "codRespuesta" in response_json:
                return {"error": str(Markup("%s %s") % (ERROR_MESSAGES["request"], response_json["codRespuesta"])), "error_reason": "rejected"}
            else:
                return {"error": str(Markup("%s<br/>%s") % (ERROR_MESSAGES["response_unknown"], response_json))}

        cdr_zip = response_json["arcCdr"]

        try:
            cdr = self.env["account.edi.format"]._l10n_pe_edi_unzip_edi_document(base64.b64decode(cdr_zip))
        except Exception as e:
            return {"error": str(Markup("%s<br/>%s") % (ERROR_MESSAGES["unzip"], e))}

        return {"cdr": cdr}


class StockLocation(models.Model):
    _inherit = 'stock.location'

    direction_id = fields.Many2one(
        comodel_name='res.partner',
        string='Address',
        help='Physical address associated with this stock location, used for the Delivery Note XML.',
    )
