from odoo import models, fields, api


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    date_st_dt = fields.Date(
        string='Payroll Month',
        help='Computed payroll month for this batch. Determined from the '
             'batch date range using the same logic as individual payslips: '
             'the month with the most days in the range is selected.',
        compute='_compute_date_st_dt',
    )

    @api.depends('date_start', 'date_end')
    def _compute_date_st_dt(self):
        payslip = self.env['hr.payslip']
        for rec in self:
            if rec.date_start and rec.date_end:
                _, _, _, rec.date_st_dt = payslip.generate_date_start_month_year(rec.date_start, rec.date_end)
            else:
                rec.date_st_dt = False

    def action_view_payslip_lines_report(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("payroll_field.action_view_payslip_lines_report")
        action['domain'] = [('slip_id.payslip_run_id', '=', self.id)]
        action['context'] = dict(self.env.context, search_default_appears_on_payslip=1, pivot_measures=['total'], pivot_column_groupby=['salary_rule_id'], pivot_row_groupby=['employee_id'])
        return action

    def action_view_payslip_lines_report_by_category(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("payroll_field.action_view_payslip_lines_report_by_category")
        action['domain'] = [('slip_id.payslip_run_id', '=', self.id)]
        action['context'] = dict(
            self.env.context,
            search_default_appears_on_payslip_category=1,
            pivot_measures=['total'],
            pivot_column_groupby=['report_category_id'],
            pivot_row_groupby=['employee_id']
        )
        return action
    def action_edit_inputs(self):
        self.ensure_one()
        tree_view_id = self.env.ref('payroll_field.hr_payslip_input_view_tree').id
        form_view_id = False # Default form view
        search_view_id = self.env.ref('payroll_field.hr_payslip_input_view_filter').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Edit Inputs',
            'res_model': 'hr.payslip.input',
            'view_mode': 'list,form',
            'views': [(tree_view_id, 'list'), (form_view_id, 'form')],
            'search_view_id': [search_view_id, 'search'],
            'domain': [('payslip_id.payslip_run_id', '=', self.id)],
            'context': dict(self.env.context, search_default_group_input_type_id=1),
        }

    def action_edit_worked_days(self):
        self.ensure_one()
        tree_view_id = self.env.ref('payroll_field.hr_payslip_worked_days_view_tree').id
        form_view_id = False # Default form view
        search_view_id = self.env.ref('payroll_field.hr_payslip_worked_days_view_filter').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Edit Worked Days',
            'res_model': 'hr.payslip.worked_days',
            'view_mode': 'list,form',
            'views': [(tree_view_id, 'list'), (form_view_id, 'form')],
            'search_view_id': [search_view_id, 'search'],
            'domain': [('payslip_id.payslip_run_id', '=', self.id)],
            'context': dict(self.env.context),
        }