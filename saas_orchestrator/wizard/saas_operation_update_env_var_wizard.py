import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


# POSIX env var name rule. Same regex enforced server-side by update_env_var.sh.
_NAME_RE = re.compile(r'^[A-Z_][A-Z0-9_]*$')


class SaasOperationUpdateEnvVarWizard(models.TransientModel):
    _name = 'saas.operation.update_env_var.wizard'
    _description = 'Update env var wizard'

    instance_id = fields.Many2one(
        'saas.instance',
        required=True,
        ondelete='cascade',
    )
    var_name = fields.Char(
        string='Variable Name',
        required=True,
        help='Env var name. Must match ^[A-Z_][A-Z0-9_]*$ (POSIX rules).',
    )
    var_value = fields.Char(
        string='Value',
        required=True,
    )
    is_secret = fields.Boolean(
        string='Mark as Secret',
        default=False,
        help='If checked, the value is masked in script log output. The '
             'on-disk env file is always 0600 regardless of this flag.',
    )

    @api.constrains('var_name')
    def _check_var_name(self):
        for rec in self:
            if rec.var_name and not _NAME_RE.match(rec.var_name):
                raise ValidationError(_(
                    "Invalid env var name %r — must match ^[A-Z_][A-Z0-9_]*$ "
                    "(letters, digits, underscores; cannot start with a digit)."
                ) % rec.var_name)

    def action_run(self):
        """Dispatch the 'update_env_var' operation declared in the catalog."""
        self.ensure_one()
        masked = '<masked>' if self.is_secret else self.var_value
        self.instance_id._dispatch_catalog_operation(
            op_code='update_env_var',
            script_args=[
                self.var_name,
                self.var_value,
                'true' if self.is_secret else 'false',
            ],
            idempotency_prefix='envvar',
            message=_("Env var %s=%s dispatched") % (self.var_name, masked),
            wizard_id=self.id,
        )
        return {'type': 'ir.actions.act_window_close'}
