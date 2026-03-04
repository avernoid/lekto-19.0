from odoo import models, fields, api
import datetime


class ReportVoucherPayroll(models.AbstractModel):
    _name = 'report.voucher_payroll.report_payslip_voucher_payroll_l10n_pe'
    _description = 'Voucher Payroll'

    @api.model
    def _get_report_values(self, docids=None, data=None):
        payslips = self.env['hr.payslip'].browse(docids)
        struct_data = self._get_structure_report(payslips)
        calc_data = self._get_calc_data(payslips)
        return {
            'doc_ids': docids,
            'docs': payslips,
            'data': data,
            'employer_sign': self.env['hr.employee'].get_employer_sign(payslips.company_id),
            'cat_lines': struct_data,
            'calc_data': calc_data
        }

    @staticmethod
    def find_weeks(start, end):
        weeks = []
        if start.weekday() == 6:
            start += datetime.timedelta(days=1)
        while start.isocalendar()[1] != end.isocalendar()[1] or (
                start.isocalendar()[1] != end.isocalendar()[1] and start.isocalendar()[0] != end.isocalendar()[0]):
            new_week = str(start.isocalendar()[1] + 100 * start.year)[4:]
            weeks.append(new_week)
            start += datetime.timedelta(7)
        weeks.append(str(start.isocalendar()[1] + 100 * start.year)[4:])
        str_weeks = ' | '.join(weeks)
        return str_weeks

    @staticmethod
    def _get_sum_worked_days_line_ids(payslip, code_list):
        days = payslip.worked_days_line_ids.filtered(lambda x: x.code in code_list)
        value = sum(line.number_of_days for line in days)
        return value

    def _get_calc_data(self, payslips):
        lines = {}
        info_new = {}

        for payslip in payslips:
            # no modified
            period = '{} | {} - {}'.format(payslip.date_start, payslip.date_from.strftime('%d/%m/%Y'), payslip.date_to.strftime('%d/%m/%Y'))
            weeks = self.find_weeks(payslip.date_from, payslip.date_to)
            hours_per_day = payslip.employee_id.resource_calendar_id.hours_per_day or 0.0

            # lines.code with string "WORK1":
            work_hours = 0
            payslip_WORK = []
            extra_hours = ['HNT_001', 'WORKN', '27', 'HE_100', 'HE_035', 'HEA_035', 'HE_025', 'HEA_025']
            for i in payslip.worked_days_line_ids:
                flag_to_add_extra_hours = True
                if not payslip.employee_id.hiden_overtime:
                    if 'WORK1' in i.code:
                        payslip_WORK.append(i)
                else:
                    # Discriminate Extra Hours
                    if 'WORK1' in i.code:
                        for hours in extra_hours:
                            if hours in i.code:
                                flag_to_add_extra_hours = False
                        if flag_to_add_extra_hours:
                            payslip_WORK.append(i)

            for line in payslip_WORK:
                work_hours = work_hours + line.number_of_hours

            noct_hours = sum(line.amount for line in payslip.input_line_ids.filtered(lambda x: x.code in ['HNT_001', 'HNF_001']))
            if noct_hours == 0.0:
                noct_hours = hours_per_day * sum(line.amount for line in payslip.input_line_ids.filtered(lambda x: x.code in ['WORKN']))

            comp_hours = sum(line.number_of_hours for line in payslip.worked_days_line_ids.filtered(lambda x: x.code in ['27']))

            hours_frdo = sum(line.amount for line in payslip.input_line_ids.filtered(lambda x: x.code in ['HE_100']))
            hours_35 = sum(line.amount for line in payslip.input_line_ids.filtered(lambda x: x.code in ['HE_035', 'HEA_035', 'HEAF_035', 'HEF_035']))
            hours_25 = sum(line.amount for line in payslip.input_line_ids.filtered(lambda x: x.code in ['HE_025', 'HEA_025', 'HEAF_025', 'HEF_025']))

            service_start_date = False
            date_start = payslip.date_start_dt
            end_date = payslip.employee_id.service_termination_date
            if date_start and end_date and date_start.strftime('%m') == end_date.strftime('%m') and date_start.strftime('%Y') == end_date.strftime('%Y'):
                service_start_date = end_date

            # modified
            work_days = 0
            holidays = 0
            break_days = 0
            sanctioned_days = 0
            not_working_days = 0
            subsidies_days = 0
            medical_rest_days = 0

            for line_worked_day in payslip.worked_days_line_ids:
                type_input = line_worked_day.work_entry_type_id.type_inputs_ids
                codes = [line.code for line in type_input]

                work_days += line_worked_day.number_of_days if 'work' in codes else 0
                holidays += line_worked_day.number_of_days if 'holidays' in codes else 0
                break_days += line_worked_day.number_of_days if 'break' in codes else 0
                sanctioned_days += line_worked_day.number_of_days if 'sanctioned' in codes else 0
                not_working_days += line_worked_day.number_of_days if 'not_working' in codes else 0
                subsidies_days += line_worked_day.number_of_days if 'subsidies' in codes else 0
                medical_rest_days += line_worked_day.number_of_days if 'medical_rest' in codes else 0

            lines.update({payslip.id: {
                'period': period,
                'weeks': weeks,
                'work_days': float('%.2f' % work_days),
                'vac_days': float('%.2f' % holidays),
                'dsc_days': float('%.2f' % break_days),
                'days_01': float('%.2f' % sanctioned_days),
                'no_lab_sub_days': float('%.2f' % not_working_days),
                'sub_days': float('%.2f' % subsidies_days),
                'desc_days': float('%.2f' % medical_rest_days),
                'work_hours': float('%.2f' % work_hours),
                'noct_hours': float('%.2f' % noct_hours),
                'comp_hours': float('%.2f' % comp_hours),
                'hours_frdo': float('%.2f' % hours_frdo),
                'hours_35': float('%.2f' % hours_35),
                'hours_25': float('%.2f' % hours_25),
                'service_start_date': service_start_date
            }})

        return lines

    @staticmethod
    def filter_per_category(payslip, category):
        data = []
        for x in payslip.line_ids.filtered(
                lambda y: y.category_id.invoice_position == category and y.salary_rule_id.appears_on_payslip):
            data.append({
                'name': x.name,
                'amount': x.amount
            })
        return data

    def complete_list_with_false(self, list_category, length):
        cat_length = len(list_category)
        if length > cat_length:
            list_category.append({
                'name': '',
                'amount': False
            })
            list_category = self.complete_list_with_false(list_category, length)
        return list_category

    @staticmethod
    def _get_total_category(category_list):
        total = sum(line['amount'] for line in category_list)
        return total

    def _get_structure_report(self, payslips):
        lines = {}
        for payslip in payslips:
            cat_1 = self.filter_per_category(payslip, 'pos_1')
            cat_2 = self.filter_per_category(payslip, 'pos_2')
            cat_3 = self.filter_per_category(payslip, 'pos_3')
            length = max(len(cat_1), len(cat_2), len(cat_3))

            total_cat1 = self._get_total_category(cat_1)
            total_cat2 = self._get_total_category(cat_2)
            total_cat3 = self._get_total_category(cat_3)
            net = self.env.ref('hr_payroll.NET', False)
            net_lines = payslip.line_ids.filtered(
                lambda x: x.category_id == net and x.salary_rule_id.appears_on_payslip)
            total_net = sum(net_l.amount for net_l in net_lines)
            cat_1 = self.complete_list_with_false(cat_1, length)
            cat_2 = self.complete_list_with_false(cat_2, length)
            cat_3 = self.complete_list_with_false(cat_3, length)
            lines.update({payslip.id: {
                'length_lines': length,
                'cat_1': cat_1,
                'cat_2': cat_2,
                'cat_3': cat_3,
                'total_cat1': total_cat1,
                'total_cat2': total_cat2,
                'total_cat3': total_cat3,
                'total_net': total_net
            }})
        return lines
