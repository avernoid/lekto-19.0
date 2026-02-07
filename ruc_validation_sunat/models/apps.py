import logging
from datetime import datetime

import requests

_logger = logging.getLogger(__name__)


class SunatPartner(object):

    def __init__(self, nro_doc, document_type, token):
        self.nro_doc = nro_doc
        self.document_type = document_type
        self.url_ruc = 'https://apiperu.dev/api/ruc'
        self.url_dni = 'https://apiperu.dev/api/dni'
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {}'.format(token)
        }

    def action_validate_api(self):
        result = False
        import time  # Import locally to avoid top-level pollution if preferred, or move to top
        for i in range(3):  # 3 attempts is standard
            try:
                instante_inicial = datetime.now()
                # Pass timeout to the internal method or handle it there
                values = self._action_validate_api()
                instante_final = datetime.now()
                tiempo = instante_final - instante_inicial
                
                if values:
                    _logger.info("SUNAT API Success (Attempt %s) for %s in %s seconds", i + 1, self.nro_doc, tiempo.seconds)
                    if self.document_type == '1':
                        result = {
                            'name': values.get('nombre_completo'),
                            'partner_name': values.get('nombres'),
                            'first_name': values.get('apellido_paterno'),
                            'second_name': values.get('apellido_materno'),
                            'vat': values.get('numero'),
                            'document_type_sunat_id': self.document_type,
                            'company_type': 'person'
                        }
                    elif self.document_type == '6':
                        ubigeo = values.get('ubigeo', [])
                        if len(ubigeo) == 3:
                            state_id = ubigeo[0]
                            city_id = ubigeo[1]
                            l10n_pe_district = ubigeo[2]
                        else:
                            state_id = False
                            city_id = False
                            l10n_pe_district = False
                        result = {
                            'name': values.get('nombre_o_razon_social'),
                            'vat': values.get('ruc'),
                            'state_contributor_sunat': values.get('estado'),
                            'condition_contributor_sunat': values.get('condicion'),
                            'street': values.get('direccion'),
                            'document_type_sunat_id': self.document_type,
                            'company_type': 'company',
                            'state_id': state_id,
                            'city_id': city_id,
                            'l10n_pe_district': l10n_pe_district
                        }
                    break
            except Exception as e:
                _logger.warning("SUNAT API Failed (Attempt %s) for %s: %s", i + 1, self.nro_doc, e)
                time.sleep(1) # Wait 1 second before retrying
                continue
        return result

    def _action_validate_api(self):
        response = False
        timeout = 10  # 10 seconds timeout
        if self.document_type == '1':
            try:
                r = requests.get('{}/{}'.format(self.url_dni, self.nro_doc), headers=self.headers, timeout=timeout)
                if not r.json()['success']:
                    return False
                response = r.json()['data']
            except Exception as e:
                raise e # Re-raise to be caught by the retry loop
        elif self.document_type == '6':
            try:
                r = requests.get(
                    '{}/{}'.format(self.url_ruc, self.nro_doc),
                    headers=self.headers,
                    timeout=timeout
                )
                if not r.json()['success']:
                    return False
                response = r.json()['data']
            except Exception as e:
                raise e # Re-raise to be caught by the retry loop
        return response
