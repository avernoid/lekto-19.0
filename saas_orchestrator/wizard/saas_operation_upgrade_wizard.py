import re

from odoo import _, fields, models
from odoo.exceptions import UserError


# Extract the version tag from any of:
#   "v2026.4.11"                              → "v2026.4.11"
#   "odoopartners/openclaw:v2026.4.11"        → "v2026.4.11"
#   "registry.example.com/foo:v2026.4.11"     → "v2026.4.11"
# Anything after the LAST colon-or-slash is treated as the tag. The script
# `upgrade.sh` then prefixes it with `odoopartners/openclaw:` itself, so
# passing the full image ref used to produce the double-prefix bug
# documented as deuda #8 of Fase 4.
_VERSION_TAG_RE = re.compile(r'([^:/\s]+)\s*$')


class SaasOperationUpgradeWizard(models.TransientModel):
    _name = 'saas.operation.upgrade.wizard'
    _description = 'Upgrade OpenClaw instance wizard'

    instance_id = fields.Many2one(
        'saas.instance',
        required=True,
        ondelete='cascade',
    )
    target_version = fields.Char(
        required=True,
        string='Target Version',
        help=(
            'Docker image tag, e.g. v2026.4.11. The wizard accepts a bare tag '
            'or a full image reference (odoopartners/openclaw:v2026.4.11) and '
            'extracts the tag automatically before dispatching.'
        ),
    )

    @staticmethod
    def _extract_tag(raw):
        """Return the version tag from any input format. Raises if empty."""
        if not raw:
            raise UserError(_("Target version is required."))
        m = _VERSION_TAG_RE.search(raw.strip())
        if not m:
            raise UserError(_(
                "Could not extract a version tag from %r. Provide a tag like "
                "'v2026.4.11' or a full image reference."
            ) % raw)
        return m.group(1)

    def action_run(self):
        """Dispatch the 'upgrade' operation declared in the blueprint catalog."""
        self.ensure_one()
        tag = self._extract_tag(self.target_version)
        self.instance_id._dispatch_catalog_operation(
            op_code='upgrade',
            script_args=[tag],
            idempotency_prefix='upgrade',
            message=_("Upgrade dispatched to target version %s") % tag,
            wizard_id=self.id,
        )
        return {'type': 'ir.actions.act_window_close'}
