from odoo import _, fields, models


class SaasOperationRestartWizard(models.TransientModel):
    _name = 'saas.operation.restart.wizard'
    _description = 'Restart OpenClaw instance wizard'

    instance_id = fields.Many2one(
        'saas.instance',
        required=True,
        ondelete='cascade',
    )

    def action_run(self):
        """Dispatch the 'restart' operation declared in the blueprint catalog."""
        self.ensure_one()
        self.instance_id._dispatch_catalog_operation(
            op_code='restart',
            script_args=[],
            idempotency_prefix='restart',
            message=_("Restart dispatched"),
            wizard_id=self.id,
        )
        return {'type': 'ir.actions.act_window_close'}
