import logging

from datetime import datetime
from odoo.fields import Date
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


class TestBasicRule(TransactionCase):

    def setUp(self):
        super(TestBasicRule, self).setUp()
        self.resource_calendar_id = self.env['resource.calendar'].create({
            'name': 'Test calendar',
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Evening', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Evening', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Evening', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Evening', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Evening', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'})
            ],
            'tz': 'America/Lima',
            'hours_per_day': 8.0,
        })
        self.weekly_struct_type_id = self.env['hr.payroll.structure.type'].create({
            'name': 'Weekly test struct type',
            'country_id': self.env.ref('base.pe').id,
            'wage_type': 'hourly',
            'default_schedule_pay_conditions': self.env.ref('payment_conditions.payment_period_3').id,
            'default_resource_calendar_id': self.env.ref('resource.resource_calendar_std').id,
            'default_work_entry_type_id': self.env.ref('hr_work_entry.work_entry_type_attendance').id,
        })
        self.weekly_struct_id = self.env['hr.payroll.structure'].create({
            'name': 'Weekly test struct',
            'type_id': self.weekly_struct_type_id.id,
            'schedule_pay_conditions': self.env.ref('payment_conditions.payment_period_3').id,
        })
        self.env.ref('basic_rule.hr_salary_rule_ism').copy(default={'struct_id': self.weekly_struct_id.id})
        life_insurance_id = self.env['life.insurance'].create({
            'name': 'Test',
            'nro': '23131',
            'start_date': Date.to_date('2020-01-01'),
            'end_date': Date.to_date('2020-12-31'),
            'hiring_term': 'test',
            'rate': 2.23,
            'amount': 1200
        })
        self.peruvian_employee_id = self.env['hr.employee'].create({
            'name': 'Developer - Employee',
            'sex': 'male',
            'birthday': '1990-05-01',
            'country_id': self.env.ref('base.pe').id,
            'tz': 'America/Lima',
            'pension_system_id': self.env.ref('types_system_pension.pension_system_2').id,
            'commission_type': 'amount',
            'resource_calendar_id': self.resource_calendar_id.id,
            'life_insurance': True,
            'life_insurance_id': life_insurance_id.id
        })
        self.weekly_contract_id = self.env['hr.version'].create({
            'date_version': Date.to_date('2018-01-01'),
            'contract_date_start': Date.to_date('2018-01-01'),
            'contract_date_end': Date.to_date('2018-12-31'),
            'name': 'Weekly Contract {}'.format(self.peruvian_employee_id.name),
            'wage': 1500.0,
            'employee_id': self.peruvian_employee_id.id,
            'structure_type_id': self.weekly_struct_type_id.id,
            'resource_calendar_id': self.resource_calendar_id.id
        })
        self.monthly_contract_id = self.env['hr.version'].create({
            'date_version': Date.to_date('2019-01-01'),
            'contract_date_start': Date.to_date('2019-01-01'),
            'name': 'Monthly Contract {}'.format(self.peruvian_employee_id.name),
            'wage': 1500.0,
            'employee_id': self.peruvian_employee_id.id,
            'structure_type_id': self.env.ref('basic_rule.hr_payroll_structure_type_general').id,
            'resource_calendar_id': self.resource_calendar_id.id
        })

    def test1_calc_ism_rule(self):
        payslip_id = self.env['hr.payslip'].create({
            'name': 'June 2020 - {}'.format(self.peruvian_employee_id.name),
            'employee_id': self.peruvian_employee_id.id,
            'date_from': datetime.strptime('2020-06-01', '%Y-%m-%d'),
            'date_to': datetime.strptime('2020-06-30', '%Y-%m-%d'),
            'struct_id': self.weekly_struct_id.id
        })
        payslip_id._onchange_employee()
        self.assertEqual(payslip_id.struct_id, self.weekly_struct_id, 'Not the same struct!')
        payslip_id.compute_sheet()
        payslip_id.action_payslip_done()
        # ISM rule
        ism_rule = payslip_id.line_ids.filtered(lambda x: x.code == 'ISM')
        self.assertEqual(ism_rule.amount, 4, 'Check calc of rule ISM!')
        _logger.info('------------ TEST OK - RULE - CODE: ISM ------------')

    def test2_calc_base_struct(self):
        payslip_id = self.env['hr.payslip'].create({
            'name': 'July 2020 - {}'.format(self.peruvian_employee_id.name),
            'employee_id': self.peruvian_employee_id.id,
            'date_from': datetime.strptime('2020-07-01', '%Y-%m-%d'),
            'date_to': datetime.strptime('2020-07-31', '%Y-%m-%d'),
        })
        payslip_id._onchange_employee()
        payslip_id.compute_sheet()
        payslip_id.action_payslip_done()

        self.assertEqual(payslip_id.state, 'validated', 'Error Payslip validated!')
        _logger.info('------------ TEST OK - BASE STRUCT ------------')
