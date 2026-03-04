from odoo import fields, models


class HrLeavePayment(models.Model):
    _name = 'hr.leave.payment'
    _description = 'Vacaciones Pagadas Sin Goce'
    _order = 'date desc'

    allocation_id = fields.Many2one(
        comodel_name='hr.leave.allocation',
        string='Asignación',
        required=True,
        ondelete='cascade',
    )
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Empleado',
        related='allocation_id.employee_id',
        store=True,
    )
    date = fields.Date(
        string='Fecha',
        required=True,
        default=fields.Date.today,
    )
    number_of_days = fields.Float(
        string='Días Pagados',
        required=True,
    )
    description = fields.Char(
        string='Concepto',
    )
