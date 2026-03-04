import logging
from odoo.tests import Form
from odoo.addons.hr.tests.common import TestHrCommon

_logger = logging.getLogger(__name__)


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
        document = self.env['l10n_latam.identification.type'].create({
            'name': 'DNI-prueba',
            'active': True
        })
        self.employee_without_image = self.env['hr.employee'].create({
            'user_id': self.user_without_image.id,
            'image_1920': False,
            'type_identification_id': document.id,
            'error_dialog': 'Mensaje de error de prueba'
        })


    def test_employee_linked_partner(self):
        user_partner = self.user_without_image.partner_id
        work_contact = self.employee_without_image.work_contact_id
        self.assertEqual(user_partner, work_contact)

    def test_employee_resource(self):
        _tz = 'Pacific/Apia'
        self.res_users_hr_officer.company_id.resource_calendar_id.tz = _tz
        Employee = self.env['hr.employee'].with_user(self.res_users_hr_officer)
        employee_form = Form(Employee)
        employee_form.name = 'Raoul Grosbedon'
        employee_form.work_email = 'raoul@example.com'
        employee = employee_form.save()
        self.assertEqual(employee.tz, _tz)

    def test_employee_from_user(self):
        _tz = 'Pacific/Apia'
        _tz2 = 'America/Tijuana'
        self.res_users_hr_officer.company_id.resource_calendar_id.tz = _tz
        self.res_users_hr_officer.tz = _tz2
        Employee = self.env['hr.employee'].with_user(self.res_users_hr_officer)
        employee_form = Form(Employee)
        employee_form.name = 'Raoul Grosbedon'
        employee_form.work_email = 'raoul@example.com'
        employee_form.user_id = self.res_users_hr_officer
        employee = employee_form.save()
        self.assertEqual(employee.name, 'Raoul Grosbedon')
        self.assertEqual(employee.work_email, self.res_users_hr_officer.email)
        self.assertEqual(employee.tz, self.res_users_hr_officer.tz)

    def test_employee_from_user_tz_no_reset(self):
        _tz = 'Pacific/Apia'
        self.res_users_hr_officer.tz = False
        Employee = self.env['hr.employee'].with_user(self.res_users_hr_officer)
        employee_form = Form(Employee)
        employee_form.name = 'Raoul Grosbedon'
        employee_form.work_email = 'raoul@example.com'
        employee_form.tz = _tz
        employee_form.user_id = self.res_users_hr_officer
        employee = employee_form.save()
        self.assertEqual(employee.name, 'Raoul Grosbedon')
        self.assertEqual(employee.work_email, self.res_users_hr_officer.email)
        self.assertEqual(employee.tz, _tz)
        _logger.info('------------------TEST Automatic_functions_rule OK--------------------------')

    def test_employee_has_avatar_even_if_it_has_no_image(self):
        self.assertTrue(self.employee_without_image.avatar_128)
        self.assertTrue(self.employee_without_image.avatar_256)
        self.assertTrue(self.employee_without_image.avatar_512)
        self.assertTrue(self.employee_without_image.avatar_1024)
        self.assertTrue(self.employee_without_image.avatar_1920)
        _logger.info('------------------TEST Automatic_functions_rule OK--------------------------')

    def test_employee_has_same_avatar_as_corresponding_user(self):
        self.assertEqual(self.employee_without_image.avatar_1920, self.user_without_image.avatar_1920)

    def test_employee_create_from_user(self):
        employee = self.env['hr.employee'].create({
            'name': 'Test User 3 - employee'
        })
        user_1, user_2, user_3 = self.env['res.users'].create([
            {
                'name': 'Test User',
                'login': 'test_user',
                'email': 'test_user@odoo.com',
            },
            {
                'name': 'Test User 2',
                'login': 'test_user_2',
                'email': 'test_user_2@odoo.com',
                'create_employee': True,
            },
            {
                'name': 'Test User 3',
                'login': 'test_user_3',
                'email': 'test_user_3@odoo.com',
                'create_employee_id': employee.id,
            },
        ])
        # Test that creating an user does not create an employee by default
        self.assertFalse(user_1.employee_id)
        # Test that setting create_employee does create the associated employee
        self.assertTrue(user_2.employee_id)
        # Test that creating an user with a given employee associates the employee correctly
        self.assertEqual(user_3.employee_id, employee)
        _logger.info('------------------TEST Automatic_functions_rule OK--------------------------')

    def test_employee_create_from_signup(self):
        # Test that an employee is not created when signin up on the website
        partner = self.env['res.partner'].create({
            'name': 'test partner'
        })
        self.env['res.users'].signup({
            'name': 'Test User',
            'login': 'test_user',
            'email': 'test_user@odoo.com',
            'password': 'test_user_password',
            'partner_id': partner.id,
        })
        self.assertFalse(self.env['res.users'].search([('login', '=', 'test_user')]).employee_id)
        _logger.info('------------------TEST Automatic_functions_rule OK--------------------------')
