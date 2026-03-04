from odoo.tests import common


class TestHrWorkEntryType(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.work_entry_type = self.env['hr.work.entry.type'].create({
            'name': 'Trabajo Home-Office',
            'code': 'THO-1000',
            'is_calc_own_rule': True,
            'round_days': 'NO'
        })
        self.company = self.env.company

        self.leave_type = self.env['hr.leave.type'].create({
            'name': 'Ausencia por Vacaciones',
            'code': 'APV-1000',
            'leave_validation_type': 'hr',
            'request_unit': 'day',
            'support_document': True,
            'time_type': 'leave',
            'company_id': self.company.id,
            'work_entry_type_id': self.work_entry_type.id,
        })

    def test_field_work_entry_type(self):
        self.assertEqual(self.work_entry_type.name, 'Trabajo Home-Office')
        self.assertEqual(self.work_entry_type.code, 'THO-1000')
        self.assertEqual(self.work_entry_type.is_calc_own_rule, True)
        self.assertEqual(self.work_entry_type.round_days, 'NO')

    def test_field_hr_leave_type(self):
        self.assertEqual(self.leave_type.name, 'Ausencia por Vacaciones')
        self.assertEqual(self.leave_type.code, 'APV-1000')
        self.assertEqual(self.leave_type.leave_validation_type, 'hr')
        self.assertEqual(self.leave_type.request_unit, 'day')
        self.assertEqual(self.leave_type.support_document, True)
        self.assertEqual(self.leave_type.time_type, 'leave')
        self.assertEqual(self.leave_type.company_id.id, self.company.id)
        self.assertEqual(self.leave_type.work_entry_type_id.id, self.work_entry_type.id)

    def test_load_entrys(self):
        hr_leave_type_data_ids = [f"automatic_leave_type.hr_leave_type_{i:02}" for i in range(1, 13)] + \
                                 [f"automatic_leave_type.hr_leave_type_{i:02}" for i in range(21, 33) if i != 23]
        hr_work_entry_type_data_ids = [f"automatic_leave_type.hr_work_entry_type_{i:02}" for i in range(1, 13)] + \
                                       [f"automatic_leave_type.hr_work_entry_type_{i:02}" for i in range(21, 33) if i != 23]

        for hr_leave_type_data_id, hr_work_entry_type_data_id in zip(hr_leave_type_data_ids, hr_work_entry_type_data_ids):
            leave_type = self.env.ref(hr_leave_type_data_id)
            work_entry = self.env.ref(hr_work_entry_type_data_id)
            self.assertTrue(leave_type)
            self.assertTrue(work_entry)