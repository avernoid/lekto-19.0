from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    

    is_employer = fields.Boolean(
        string='Is Employer',
        help='Check this box if this employee acts as an employer or legal representative. This allows the system to use their signature on official documents such as payroll vouchers.',
        groups="hr.group_hr_user"
    )
    employer_sign = fields.Image(
        string='Employer Signature',
        copy=False,
        attachment=True,
        max_width=128, max_height=128,
        help='Upload the digital signature of the employer. This image will be printed on the automated payroll vouchers and other HR documents to validate them.',
        groups="hr.group_hr_user"
    )

    @api.onchange('is_employer')
    def onchange_is_employer(self):
        if not self.is_employer:
            self.employer_sign = False

    def get_employer_sign(self, company_id):
        signs = self.env['hr.employee'].search([('is_employer', '=', True), ('employer_sign', '!=', False)])

        for sign in signs:
            if sign.company_id.id == company_id.id:
                values = {
                    'name': sign.name.upper(),
                    'job_title': sign.job_title.upper() if sign.job_title else '',
                    'sign': sign.employer_sign,
                    'sign_decode': sign.employer_sign.decode('utf-8'),
                    'type_identification_id': sign.type_identification_id.name.upper() if sign.type_identification_id else '',
                    'identification_id': sign.identification_id or ''
                }
                return values
        return {}