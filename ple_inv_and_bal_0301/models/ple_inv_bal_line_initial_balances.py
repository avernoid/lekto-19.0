from odoo import fields, models, api

class PleInvBalLinesInitial(models.Model):
    _name = 'ple.inv.bal.line.initial.balances'
    _description = 'Estado de Situación financiera de saldos iniciales - Líneas'
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
    code_eeff = fields.Char(
        string='Código del rubro del EEFF', 
        compute='calculate_name_code'
    )
    nombre_eeff = fields.Char(
        string='Nombre del rubro del EEFF', 
        compute='calculate_name_code'
    )

    @api.depends('code_eeff','nombre_eeff')
    def calculate_name_code(self):
        for rec in self:
            data = rec.eeff_ple_id
            rec.code_eeff = data.code
            rec.nombre_eeff = data.description