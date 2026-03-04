from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    judicial_discount = fields.Float(
        string='Judicial Discount',
        help='Amount to be discounted from the employee for judicial retention',
        groups="hr.group_hr_user"
    )
    judicial_discount_percent = fields.Float(
        string='Judicial Discount Percentage',
        help='Percentage of the salary to be discounted for judicial retention',
        groups="hr.group_hr_user"
    )
    exists_beneficiary = fields.Boolean(
        string='Exists Beneficiary?',
        help='Check if there is a specific beneficiary for the retention',
        groups="hr.group_hr_user"
    )
    beneficiary = fields.Many2one(
        'res.partner', 'Beneficiary',
        help='Select the contact (partner) designated to receive the funds',
        groups="hr.group_hr_user", tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    bond = fields.Char(
        string='Bond',
        help='Specify the relationship between the employee and the beneficiary (e.g., Child, Spouse)',
        size=10,
        groups="hr.group_hr_user"
    )
    card_type_id = fields.Many2one(
        comodel_name="l10n_latam.identification.type",
        string='Beneficiary Document Type',
        help='Select the identification document type of the beneficiary',
        groups="hr.group_hr_user")
    card_id = fields.Char(
        string='Document Number',
        help='Enter the identification document number of the beneficiary',
        groups="hr.group_hr_user"
    )
    payment_type = fields.Many2one(
        comodel_name='payment.type',
        string='Judicial Payment Type',
        help='Select the method by which the retention will be paid',
        groups="hr.group_hr_user"
    )
    pay_code = fields.Char(
        string="Journal Code",
        help='Code of the payment type journal',
        related="payment_type.code",
        groups="hr.group_hr_user"
    )

    settlement_retention = fields.Boolean(
        string='Retain from Settlement?',
        help='Check if the retention should also be applied to the final settlement',
        groups="hr.group_hr_user",
        default=False
    )
    retention_on = fields.Selection([
        ('total_income', 'Total Income'),
        ('affection_income', 'Taxable Income'),
        ('unaffected_income', 'Non-Taxable Income'),
        ('net_income', 'Net Income'),
        ('net_payable', 'Net Payable Amount'),
    ],
        string="Retention Based On",
        help='Select the salary base from which the retention will be calculated',
        groups="hr.group_hr_user"
    )
    account_number = fields.Many2one(
        'res.partner.bank', 
        string="Account Number", 
        help='Select the bank account of the beneficiary destined to receive the deposits',
        groups="hr.group_hr_user")
    bank = fields.Char(
        compute="_name_bank", 
        string='Bank', 
        help='Name of the bank associated to the beneficiary account',
        readonly=True, 
        groups="hr.group_hr_user")
    cci = fields.Char(
        compute="_mostrarcci", 
        string='Interbank Code (CCI)', 
        help='Interbank code associated to the beneficiary account',
        readonly=True, 
        groups="hr.group_hr_user")
    start_date = fields.Date(
        string='Valid From', 
        help='Start date for the judicial retention application',
        groups="hr.group_hr_user")
    end_date = fields.Date(
        string='Valid To', 
        help='End date for the judicial retention application',
        groups="hr.group_hr_user")
    retention_amount = fields.Float(
        string="Maximum Retention Amount", 
        help='Maximum amount or cap to be retained from the employee',
        default=0, 
        groups="hr.group_hr_user")

    @api.depends('account_number')
    def _mostrarcci(self):
        for employee in self:
            if employee.account_number:
                employee.cci = employee.account_number.cci
            else:
                employee.cci = ' '

    @api.depends('account_number')
    def _name_bank(self):
        for employee in self:
            if employee.account_number and employee.account_number.bank_id:
                employee.bank = employee.account_number.bank_id.name
            else:
                employee.bank = ' '
