import logging
from datetime import datetime

import requests

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

API_TIMEOUT = 30


class SaasOpenclawVersion(models.Model):
    _name = 'saas.openclaw.version'
    _description = 'OpenClaw Version Registry'
    _order = 'built_at desc'

    name = fields.Char(string='Tag', required=True, index=True)
    upstream_tag = fields.Char(required=True)
    built_at = fields.Datetime(required=True)
    promoted_to_stable = fields.Datetime()
    status = fields.Selection([
        ('ok', 'OK'),
        ('broken', 'Broken'),
        ('deprecated', 'Deprecated'),
    ], required=True, default='ok')
    notes = fields.Text()
    release_notes_url = fields.Char()
    active = fields.Boolean(default=True)

    _tag_unique = models.Constraint(
        'UNIQUE(name)',
        'Version tag must be unique.',
    )

    @api.model
    def _cron_sync_versions(self):
        """Sync version registry from the orchestrator API.

        Called by the daily cron. Fetches GET /versions from the orchestrator
        and upserts into this model. Versions removed from the orchestrator
        are marked inactive (not deleted) to preserve FK integrity.
        """
        ICP = self.env['ir.config_parameter'].sudo()
        base_url = ICP.get_param('saas.orchestrator.url', '').rstrip('/')
        api_key = ICP.get_param('saas.orchestrator.api_key', '')
        if not base_url or not api_key:
            _logger.warning("Orchestrator URL/key not configured, skipping version sync")
            return

        try:
            resp = requests.get(
                f"{base_url}/versions",
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=API_TIMEOUT,
            )
            resp.raise_for_status()
        except Exception as e:
            _logger.error("Version sync failed: %s", e)
            return

        data = resp.json()
        remote_tags = set()

        def _parse_dt(val):
            """Parse a datetime string from the API, stripping timezone info."""
            if not val:
                return False
            try:
                dt = datetime.fromisoformat(val)
                return dt.replace(tzinfo=None).strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                return False

        for item in data.get('items', []):
            tag = item['tag']
            remote_tags.add(tag)
            existing = self.search([('name', '=', tag)], limit=1)
            vals = {
                'name': tag,
                'upstream_tag': item.get('upstream_tag', tag),
                'built_at': _parse_dt(item.get('built_at')),
                'promoted_to_stable': _parse_dt(item.get('promoted_to_stable')),
                'status': item.get('status', 'ok'),
                'notes': item.get('notes'),
                'release_notes_url': item.get('release_notes_url'),
                'active': True,
            }
            if existing:
                existing.write(vals)
            else:
                self.create(vals)

        # Mark versions no longer in the orchestrator as inactive
        stale = self.search([('name', 'not in', list(remote_tags)), ('active', '=', True)])
        if stale:
            stale.write({'active': False})
            _logger.info("Marked %d stale versions inactive", len(stale))
