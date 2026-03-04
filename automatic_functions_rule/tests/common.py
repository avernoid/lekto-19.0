from datetime import date

from dateutil.relativedelta import relativedelta
from odoo.tests.common import TransactionCase


class TestPayslipBase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.dep_rd = cls.env['hr.department'].create({
            'name': 'Research & Development - Test',
        })

        cls.structure_type = cls.env['hr.payroll.structure.type'].create({
            'name': 'Test - Developer',
        })

        cls.richard_emp = cls.env['hr.employee'].create({
            'name': 'Richard',
            'department_id': cls.dep_rd.id,
            'date_version': date(2015, 1, 1),
            'contract_date_start': date(2015, 1, 1),
            'contract_date_end': date.today() + relativedelta(years=2),
            'wage': 5000,
            'structure_type_id': cls.structure_type.id,
        })
        cls.richard_version = cls.richard_emp.version_id

        cls.work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'Extra attendance',
            'is_leave': False,
            'code': 'WORKTEST200',
        })

        cls.work_entry_type_unpaid = cls.env['hr.work.entry.type'].create({
            'name': 'Unpaid Leave',
            'is_leave': True,
            'code': 'LEAVETEST300',
            'round_days': 'HALF',
            'round_days_type': 'DOWN',
        })

        # Salary structure
        cls.developer_pay_structure = cls.env['hr.payroll.structure'].create({
            'name': 'Salary Structure for Software Developer',
            'type_id': cls.structure_type.id,
            'unpaid_work_entry_type_ids': [(4, cls.work_entry_type_unpaid.id, False)],
        })

        cls.structure_type.default_struct_id = cls.developer_pay_structure

        # Input type for structure injection tests
        cls.input_type = cls.env['hr.payslip.input.type'].create({
            'name': 'Test Input Type',
            'code': 'TESTINP',
        })
