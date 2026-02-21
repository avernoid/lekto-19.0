from odoo import fields, models


class PleEeffAccountConfig(models.Model):
    _name = 'ple.eeff.account.config'
    _description = 'EEFF PLE Account Configuration'
    _order = 'sequence, id'

    name = fields.Char(
        string='Account Code',
        required=True,
        help="Código de la cuenta contable, e.g. 1010000",
    )
    sequence = fields.Integer(default=10)

    # Account Identification (for dynamic XML ID construction)
    account_prefix = fields.Char(
        string='XML Prefix',
        default='account',
        required=True,
        help="XML ID prefix. Default: account",
    )
    account_suffix = fields.Char(
        string='XML Suffix',
        required=True,
        help="XML ID suffix, e.g. chart101. "
             "The full XML ID is built as: {prefix}.{company_id}_{suffix}",
    )

    # Target EEFF
    eeff_ple_id = fields.Many2one(
        comodel_name='eeff.ple',
        string='Rubro EEFF (3.1)',
        required=True,
        help="Rubro del Estado de Situación Financiera al que pertenece esta cuenta.",
    )

    internal_group = fields.Selection(
        selection=[
            ('asset', 'Activo'),
            ('liability', 'Pasivo'),
            ('equity', 'Capital'),
        ],
        string='Grupo interno',
        help="Grupo interno de la cuenta contable (referencia visual).",
    )

    notes = fields.Text(string='Notas')

    def action_update_eeff_wizard(self):
        """Opens the wizard with this record pre-selected."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Actualizar Rubros EEFF',
            'res_model': 'ple.update.eeff.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_config_ids': [self.id],
            },
        }
