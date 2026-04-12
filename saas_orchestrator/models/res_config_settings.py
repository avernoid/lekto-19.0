from odoo import api, fields, models, _
from odoo.exceptions import UserError
import requests
import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    saas_orchestrator_url = fields.Char(
        string='Orchestrator URL',
        config_parameter='saas.orchestrator.url',
        default='https://api.orquestio.com',
        help="Base URL of the Orquestio orchestrator API.",
    )
    saas_orchestrator_api_key = fields.Char(
        string='Orchestrator API Key',
        config_parameter='saas.orchestrator.api_key',
        help="Bearer token used to authenticate against the orchestrator API. "
             "Stored in System Parameters; visible only to administrators.",
    )

    def action_test_orchestrator_connection(self):
        """Test the connection to the orchestrator by hitting /health.

        Returns a notification with success or failure. Does NOT save the
        settings — the user must click Save first if they edited the values.
        """
        self.ensure_one()
        url = (self.saas_orchestrator_url or '').rstrip('/')
        api_key = self.saas_orchestrator_api_key or ''
        if not url:
            raise UserError(_("Please set the Orchestrator URL first."))
        try:
            # /health is public — no auth needed, but we send the key anyway
            # to also validate it is well-formed
            headers = {'Authorization': f'Bearer {api_key}'} if api_key else {}
            response = requests.get(f"{url}/health", headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            checks = data.get('checks', {})
            status = data.get('status', 'unknown')
            if status == 'healthy':
                msg = _("Connection successful. Orchestrator status: %s. Checks: %s") % (status, checks)
                msg_type = 'success'
            else:
                msg = _("Orchestrator reachable but reports status: %s. Checks: %s") % (status, checks)
                msg_type = 'warning'
        except requests.exceptions.ConnectionError:
            raise UserError(_("Cannot connect to orchestrator at %s. Check the URL and your network.") % url)
        except requests.exceptions.Timeout:
            raise UserError(_("Connection to %s timed out (10s).") % url)
        except requests.exceptions.HTTPError as e:
            raise UserError(_("Orchestrator responded with HTTP %s: %s") % (e.response.status_code, e.response.text[:200]))
        except Exception as e:
            _logger.exception("Unexpected error testing orchestrator connection")
            raise UserError(_("Unexpected error: %s") % e)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Orchestrator Connection'),
                'message': msg,
                'type': msg_type,
                'sticky': False,
            },
        }
