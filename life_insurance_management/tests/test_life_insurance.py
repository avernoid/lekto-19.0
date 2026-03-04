from odoo.tests import Form
from odoo.addons.hr.tests.common import TestHrCommon


class TestHrEmployee(TestHrCommon):

    def setUp(self):
        super().setUp()
        self.user_without_image = self.env['res.users'].create({
            'name': 'Marc Demo',
            'email': 'mark.brown23@example.com',
            'image_1920': False,
            'login': 'demo_1',
            'password': 'demo_123'
        })
        insurance_record = self.env['life.insurance'].create({
            'name': 'Marc Demo',
            'nro': '6574',
            'hiring_term': 'Plazo prueba',
            'start_date': '2022-06-01',
            'end_date': '2023-06-01',
            'rate': 2.4,
            'amount': 8
        })
        self.employee_without_image = self.env['hr.employee'].create({
            'user_id': self.user_without_image.id,
            'image_1920': False,
            'life_insurance': True,
            'life_insurance_id': insurance_record.id

        })

    def test_employee_linked_partner(self):
        user_partner = self.user_without_image.partner_id
        work_contact = self.employee_without_image.work_contact_id
        self.assertEqual(user_partner, work_contact)
        print('------TEST INSURANCE MANAGEMENT OK--------------')