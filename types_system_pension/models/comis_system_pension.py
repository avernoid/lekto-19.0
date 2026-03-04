from odoo import fields, models


class ComisSystemPension(models.Model):
    _name = 'comis.system.pension'
    _description = 'AFP Commission Rate'

    date_from = fields.Date(
        string='From',
        required=True,
        help="Start date of the validity period for this commission rate. The payroll engine uses the payslip period "
             "to look up the applicable commission record."
    )
    date_to = fields.Date(
        string='To',
        required=True,
        help="End date of the validity period for this commission rate. Together with the From date, "
             "this defines the period during which these rates are applicable."
    )
    fund = fields.Float(
        string='Fund',
        help="AFP Fund (Fondo) commission rate as a decimal percentage (e.g., 0.10 for 10%). "
             "This rate applies to employees enrolled in the fund-based commission scheme."
    )
    bonus = fields.Float(
        string='Bonus',
        help="AFP Bonus (Prima) commission rate as a decimal percentage. This is an insurance premium "
             "charged by the AFP for disability and survivor coverage."
    )
    mixed_flow = fields.Float(
        string='Mixed / Flow',
        help="AFP Mixed-Flow (Flujo / Mixta) commission rate as a decimal percentage. Applies to employees "
             "under the mixed commission type where both flow and fund components are charged."
    )
    flow = fields.Float(
        string='Flow',
        help="AFP Flow (Flujo) commission rate as a decimal percentage. This rate is charged as a percentage "
             "of the employee's gross salary under the flow-based commission scheme."
    )
    balance = fields.Float(
        string='Balance',
        help="AFP Balance (Saldo) commission rate as a decimal percentage. This rate is charged as a percentage "
             "of the employee's managed fund balance under the balance commission scheme."
    )
    pension_id = fields.Many2one(
        comodel_name='pension.system',
        string='Pension System',
        help="The AFP pension system to which these commission rates belong. "
             "Each AFP has its own rate schedule by period."
    )
