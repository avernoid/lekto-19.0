from odoo import fields, models


class HrWorkEntryType(models.Model):
    _inherit = 'hr.work.entry.type'

    is_calc_own_rule = fields.Boolean(
        string='¿Es calculado por su propia regla?',
        help="If checked, this work entry type is computed by its own payroll rule "
             "instead of the standard attendance rule.",
    )
