from odoo import _, fields, models
from odoo.exceptions import UserError


class SaasOperationRotatePasswordWizard(models.TransientModel):
    _name = 'saas.operation.rotate_password.wizard'
    _description = 'Rotate gateway password wizard'

    instance_id = fields.Many2one(
        'saas.instance',
        required=True,
        ondelete='cascade',
    )
    notify_client = fields.Boolean(
        string='Notify Client',
        default=False,
        help='If checked, the orchestrator will (in the future) push the new '
             'password to the client via webhook. Currently a stub — the script '
             'accepts the flag but no notification is sent.',
    )
    confirmed = fields.Boolean(
        string='I understand active sessions will be invalidated',
        default=False,
    )

    def action_run(self):
        """Dispatch the 'rotate_password' operation declared in the catalog."""
        self.ensure_one()
        if not self.confirmed:
            raise UserError(_(
                "Please confirm that you understand active sessions will be "
                "invalidated by this rotation."
            ))
        self.instance_id._dispatch_catalog_operation(
            op_code='rotate_password',
            script_args=['true' if self.notify_client else 'false'],
            idempotency_prefix='rotpwd',
            message=_("Gateway password rotation dispatched"),
            wizard_id=self.id,
        )
        return {'type': 'ir.actions.act_window_close'}
