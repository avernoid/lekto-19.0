import base64

from odoo.exceptions import ValidationError
from odoo.tools.misc import format_date
from odoo.tools.safe_eval import safe_eval

from odoo import _, api, fields, models





class HrPayslip(models.Model):
    _name = 'hr.payslip'
    _inherit = ['hr.payslip', 'portal.mixin']

    employee_mail = fields.Char(
        string='Employee Email',
        related='employee_id.private_email',
        help=(
            'The private email address of the employee, used as the portal access email. '
            'This field is automatically populated from the employee record (Private Information tab). '
            'If empty, the employee will not receive secure portal notifications.'
        ),
    )
    status = fields.Selection(
        selection=[
            ('to_sign', 'To Sign'),
            ('signed', 'Signed'),
        ],
        string='Signature Status',
        default='to_sign',
        readonly=True,
        help=(
            'Indicates whether the employee has digitally signed this payslip via the portal. '
            '"To Sign" means the payslip has been sent but the employee has not yet signed it. '
            '"Signed" means the employee has submitted their digital signature through the portal link.'
        ),
    )
    signature = fields.Image(
        string='Employee Signature',
        copy=False,
        attachment=True,
        max_width=128, max_height=128,
        help=(
            'The digital signature image submitted by the employee through the secure payslip portal. '
            'Once the employee signs via the portal link, this image is stored here as proof of acknowledgment. '
            'The signature is stored as a 128x128 pixel image attachment.'
        ),
    )
    display_name = fields.Char(
        compute='_compute_display_name',
    )

    def _compute_access_url(self):
        super(HrPayslip, self)._compute_access_url()
        for payslip in self:
            payslip.access_url = '/my/payslip/%s' % (payslip.id)

    def get_portal_url(self, suffix=None, report_type=None, download=None, accept_pay_voucher=None, query_string=None,
                       anchor=None):
        url = self.access_url + '%s?access_token=%s%s%s%s%s%s' % (
            suffix if suffix else '',
            self._portal_ensure_token(),
            '&report_type=%s' % report_type if report_type else '',
            '&download=true' if download else '',
            '&accept_pay_voucher=true' if accept_pay_voucher else '',
            query_string if query_string else '',
            '#%s' % anchor if anchor else ''
        )
        return url

    def _get_report_base_filename(self):
        self.ensure_one()
        return '%s - %s' % (_('Payslip'), self.name)

    @api.depends('employee_id', 'date_from')
    def _compute_display_name(self):
        for slip in self:
            slip.display_name = False

        for slip in self.filtered(lambda p: p.employee_id and p.date_from):
            lang = slip.employee_id.sudo().address_id.lang or self.env.user.lang
            context = {'lang': lang}
            del context
            slip.display_name = 'Boleta de pago - %(dates)s' % {
                'dates': format_date(self.env, slip.date_from, date_format="MMMM y", lang_code=lang)
            }

    def action_send_mail_employees(self):
        payslip_ids = self.filtered(lambda x: x.state == 'validated' or x.state == 'paid')
        counter_mail = 1
        data_employee = dict()

        for payslip in payslip_ids:
            if payslip.employee_id.id:
                data_employee[payslip.employee_id] = payslip.employee_id.id

        error_dialog_mail = ''
        for employee in data_employee:
            if not employee.work_email:
                error_dialog_mail += '\n[%s] %s' % (counter_mail, employee.name)
                counter_mail += counter_mail

        if counter_mail > 1:
            raise ValidationError(error_dialog_mail)

        for rec in payslip_ids:
            mail_obj = self.env['mail.compose.message'].with_context({
                'default_template_id': self.env.ref('voucher_sending.mail_template_hr_payslip_by_employee').id,
                'default_model': 'hr.payslip',
                'custom_layout': "mail.mail_notification_light",
                'default_res_ids': [rec.id],
                'default_composition_mode': 'comment',
                'force_email': True,
                'mark_so_as_sent': True
            })
            report_id = self.env['ir.attachment'].search([
                ('res_id', '=', rec.id),
                ('res_model', '=', 'hr.payslip'),
            ])  
            if not report_id or len(report_id) != 1:
                report_id = rec.generate_report_manually()
            mail_id = mail_obj.create({'attachment_ids': [report_id.id]})
            mail_id.action_send_mail()

    def generate_report_manually(self):
        
        if not self.struct_id or not self.struct_id.report_id:
            report = self.env.ref('hr_payroll.action_report_payslip', False)
        else:
            report = self.struct_id.report_id
        pdf_content, content_type = report._render_qweb_pdf(report.report_name, res_ids=self.ids)
        if self.struct_id.report_id.print_report_name:
            pdf_name = safe_eval(self.struct_id.report_id.print_report_name, {'object': self})
        else:
            pdf_name = _("Payslip")
            
        if not pdf_name.lower().endswith('.pdf'):
            pdf_name = f"{pdf_name}.pdf"
        
        attach_id = self.env['ir.attachment'].create({
            'name': pdf_name,
            'type': 'binary',
            'datas': base64.encodebytes(pdf_content),
            'res_model': self._name,
            'res_id': self.id
        })
        return attach_id
