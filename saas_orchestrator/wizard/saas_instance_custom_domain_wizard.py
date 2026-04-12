import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


_HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)"
    r"(?:(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)\.)+"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"
)


class SaasInstanceCustomDomainWizard(models.TransientModel):
    _name = 'saas.instance.custom_domain.wizard'
    _description = 'Configure BYO custom domain wizard'

    instance_id = fields.Many2one(
        'saas.instance',
        required=True,
        ondelete='cascade',
    )
    state = fields.Selection([
        ('input', 'Input'),
        ('instructions', 'Instructions'),
    ], default='input', required=True)

    domain = fields.Char(
        string='Custom Domain',
        required=True,
        help='Hostname you own and want to expose this instance under, e.g. ai.acme.com',
    )
    cname_target = fields.Char(string='CNAME Target', readonly=True)
    # Vestigial — kept so existing tests and views don't blow up. In Plan A
    # this carried Cloudflare's hostname status; Plan B has no equivalent
    # since the local DB is the source of truth. Always None in Plan B.
    cf_status = fields.Char(string='Status', readonly=True)

    @api.constrains('domain')
    def _check_domain(self):
        for rec in self:
            if rec.domain:
                normalized = rec.domain.strip().lower()
                if not _HOSTNAME_RE.match(normalized):
                    raise ValidationError(_(
                        "Invalid domain %r. Use a valid lowercase ASCII hostname "
                        "like ai.acme.com (no underscores, no IDN, at least one dot)."
                    ) % rec.domain)

    def action_register(self):
        """Step 1 → call orchestrator to register the domain (Plan B).

        Plan B: the orchestrator dispatches `add_custom_domain` to the
        customer EC2 via the control plane. The script obtains the cert
        and installs nginx; a post-success hook flips status to 'active'.
        """
        self.ensure_one()
        normalized = (self.domain or '').strip().lower()
        if not normalized:
            raise UserError(_("Domain is required."))

        instance = self.instance_id
        try:
            response = instance._api_call(
                'POST',
                f'/instances/{instance.name}/custom-domain',
                {'domain': normalized},
            )
        except UserError as e:
            msg = str(e)
            if '409' in msg:
                raise UserError(_(
                    "This domain is already registered (either on this instance "
                    "or on another). Use 'Remove custom domain' first if needed."
                )) from e
            if '503' in msg:
                raise UserError(_(
                    "The control plane is temporarily unavailable. Wait a few "
                    "seconds and try again."
                )) from e
            raise

        self.write({
            'domain': normalized,
            'cname_target': response.get('cname_target'),
            'cf_status': response.get('cf_status'),
            'state': 'instructions',
        })
        instance.write({
            'custom_domain': normalized,
            'custom_domain_status': response.get('status') or 'pending',
        })
        instance.message_post(body=_(
            "Custom domain %s registered (status %s).",
            normalized, response.get('status') or 'pending',
        ))

        # Reopen the wizard at the instructions step.
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_instance_id': instance.id},
        }

    def action_close(self):
        """Step 2 → user confirms they've set up the CNAME and closes the wizard.

        The wizard does NOT poll for activation — that happens via the
        Refresh button on the instance form. Polling here would block the
        UI for an arbitrary amount of time (CF takes seconds to minutes
        depending on DNS propagation).
        """
        self.ensure_one()
        return {'type': 'ir.actions.act_window_close'}
