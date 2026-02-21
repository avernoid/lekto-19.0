from odoo import _, fields, models
import logging

_logger = logging.getLogger(__name__)


class PleUpdateEeffWizard(models.TransientModel):
    _name = 'ple.update.eeff.wizard'
    _description = 'Wizard to Mass-Assign EEFF Rubros to Accounts'

    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company,
    )
    config_ids = fields.Many2many(
        'ple.eeff.account.config',
        string='Configuraciones a aplicar',
        required=True,
    )

    def action_execute(self):
        self.ensure_one()
        _logger.info(
            "EEFF WIZARD: Starting EEFF assignment for Company %s (id=%s)",
            self.company_id.name, self.company_id.id,
        )

        success_count = 0
        error_count = 0

        for config in self.config_ids:
            # Build dynamic XML ID: e.g. account.1_chart101
            xml_id = "%s.%s_%s" % (
                config.account_prefix,
                self.company_id.id,
                config.account_suffix,
            )

            account = self.env.ref(xml_id, raise_if_not_found=False)

            if not account:
                _logger.warning("EEFF WIZARD: Account NOT FOUND for XML ID: %s", xml_id)
                error_count += 1
                continue

            account.write({'eeff_ple_id': config.eeff_ple_id.id})
            success_count += 1

        message = _(
            "Actualización completa. Éxito: %(success)s, No encontradas: %(errors)s",
            success=success_count,
            errors=error_count,
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Resultado asignación EEFF"),
                'message': message,
                'sticky': False,
                'type': 'warning' if error_count > 0 else 'success',
            },
        }
