import requests
from requests.exceptions import URLRequired, HTTPError

_original_raise_for_status = requests.models.Response.raise_for_status

def custom_raise_for_status(self):
    """
    Mejora el manejo de los errores en la respuesta de SUNAT mostrando el contenido del error en la petición.
    """
    try:
        _original_raise_for_status(self)
    except HTTPError:
        reason = getattr(self, "reason", "")
        url = getattr(self, "url", "")
        content = self.content

        if 400 <= self.status_code < 500:
            http_error_msg = (
                f"{self.status_code} Client Error: {reason} for url: {url}\nContent: {content}"
            )
        elif 500 <= self.status_code < 600:
            http_error_msg = (
                f"{self.status_code} Server Error: {reason} for url: {url}\nContent: {content}"
            )
        else:
            http_error_msg = ""

        if http_error_msg:
            # FIX: Para evitar error en l10n_pe_edi_stock que valida solo HTTPError
            if self.status_code == 401 and 'api-cpe.sunat.gob.pe' in url:
                raise HTTPError(http_error_msg, response=self)
            else:
                raise URLRequired(http_error_msg, response=self)
requests.models.Response.raise_for_status = custom_raise_for_status
