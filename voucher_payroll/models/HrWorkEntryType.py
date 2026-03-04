from odoo import models, fields


class HrWorkEntryType(models.Model):
    _inherit = 'hr.work.entry.type'

    type_inputs_ids = fields.Many2many(
        'type.inputs',
        string='Day Type Inputs',
        help=(
            "Associates this work entry type with one or more type input codes that determine how worked days "
            "are classified on the pay slip voucher. "
            "For example, linking to the 'work' code will cause payslip lines of this work entry type to count "
            "as regular Work Days on the voucher. "
            "Linking to 'holidays' counts as Vacation Days, 'medical_rest' as Medical Rest Days, etc. "
            "A single work entry type can belong to multiple input categories if needed."
        )
    )
