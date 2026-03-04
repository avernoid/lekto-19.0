from odoo import fields, models


class TopeAFP(models.Model):
    _name = 'tope.afp'
    _description = 'AFP Monthly Cap'

    date_from = fields.Date(
        string='From',
        required=True,
        help="Start date of the period for which this AFP monthly cap is applicable. "
             "The payroll engine uses the payslip date to find the correct cap record."
    )
    date_to = fields.Date(
        string='To',
        required=True,
        help="End date of the period for which this AFP monthly cap is applicable. "
             "Together with the From date, this defines the window of validity for this cap."
    )
    top = fields.Float(
        string='Monthly Cap (PEN)',
        help="Maximum monthly contribution base in Peruvian Soles (PEN) for AFP deduction calculations. "
             "Any employee salary above this amount will have their AFP deduction calculated on this cap value, "
             "not on their full salary. This value is updated periodically by the SBS (Superintendencia de Banca y Seguros)."
    )

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '[%s - %s] %s' % (rec.date_from or '', rec.date_to or '', rec.top)
