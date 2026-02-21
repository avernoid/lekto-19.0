from odoo import fields, models, api

class PleInvBalLines(models.Model):
    _name = 'ple.report.inv.bal.line'
    _description = 'Estado de Situación financiera - Líneas'
    _order = 'sequence desc'

    sequence = fields.Integer(
        string='Secuencia'
    )
    ple_report_inv_val_id = fields.Many2one(
        comodel_name='ple.report.inv.bal',
        string='Reporte de Estado de Situación financiera'
    )
    name = fields.Char(
        string='Periodo'
    )
    catalog_code = fields.Char(
        string='Código de catálogo'
    )
    financial_state_code = fields.Char(
        string='Código del Rubro del Estado Financiero'
    )
    eeff_ple_id = fields.Many2one(
        string='Rubro EEFF PLE',
        comodel_name='eeff.ple'
    )
    credit = fields.Char(
        string='Saldo del Rubro Contable'
    )
    state = fields.Char(
        string='Indica el estado de la operación'
    )
    account_ids = fields.Many2many(
        comodel_name='account.account',
        string='Cuentas',
        readonly=True
    )
    description = fields.Char(
        string='Descripción'
    )
