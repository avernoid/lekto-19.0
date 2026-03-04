from odoo import api, models


class ReportsJudicialRetention(models.AbstractModel):
    _name = 'report.judicial_retention_fields.template_judicial_report'
    _description = 'Payslip Judicial Retention'

    @api.model
    def _get_report_values(self, docids=None, data=None):
        payslips = self.env['hr.payslip'].browse(docids)
        employer_sign = self.env['hr.employee'].get_employer_sign(payslips.company_id)
        return {
            'doc_ids': docids,
            'docs': payslips,
            'data': data,
            'doc_model': 'hr.payslip',
            'employer_sign': employer_sign
        }
