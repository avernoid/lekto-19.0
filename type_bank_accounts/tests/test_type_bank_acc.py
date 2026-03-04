from odoo.tests.common import TransactionCase


class TestHrEmployeeBankAccount(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.ref('base.main_company')
        self.env.user.company_id = self.company

        # Crear banco de prueba
        self.bank = self.env['res.bank'].create({
            'name': 'BCP',
            'bic': 'BCPLPEPL1',
        })

        # Crear contacto para el empleado|
        self.partner = self.env['res.partner'].create({
            'name': 'Test Supplier Dany Chavez',
            'is_company': True,
            'vat': '75097420',
            'street': 'Test Street',
        })
        
        # Crear empleado de prueba
        self.employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
            'work_contact_id': self.partner.id,
        })

    def _create_asserts(self, employee, account_salary_bank='', type_salary_bank='', account_cts_bank='', type_cts_bank=''):
        self.assertEqual(employee.account_salary_bank, account_salary_bank)
        self.assertEqual(employee.type_salary_bank, type_salary_bank)
        self.assertEqual(employee.account_cts_bank, account_cts_bank)
        self.assertEqual(employee.type_cts_bank, type_cts_bank)

    def test_01_fields_exist_in_hr_employee(self):
        """Test para validar que los campos existen en el modelo hr.employee"""
        employee = self.env['hr.employee']
        
        # Verificar que los campos existen en el modelo hr.employee
        self.assertTrue(hasattr(employee, 'account_salary_bank'), "El campo 'account_salary_bank' no existe")
        self.assertTrue(hasattr(employee, 'type_salary_bank'), "El campo 'type_salary_bank' no existe")
        self.assertTrue(hasattr(employee, 'account_cts_bank'), "El campo 'account_cts_bank' no existe")
        self.assertTrue(hasattr(employee, 'type_cts_bank'), "El campo 'type_cts_bank' no existe")
        print("<<<<<<<<<< TEST 1 PASSED >>>>>>>>>>")

    def test_02_fields_exist_in_res_partner_bank(self):
        """Test para validar que los campos existen en el modelo res.partner.bank"""
        partner_bank = self.env['res.partner.bank']
        
        # Verificar que los campos existen en el modelo res.partner.bank
        self.assertTrue(hasattr(partner_bank, 'acc_type'), "El campo 'acc_type' no existe")
        self.assertTrue(hasattr(partner_bank, 'type_bank_code'), "El campo 'type_bank_code' no existe")
        self.assertTrue(hasattr(partner_bank, 'cci'), "El campo 'cci' no existe")
        print("<<<<<<<<<< TEST 2 PASSED >>>>>>>>>>")

    def test_03_compute_bank_accounts_empty(self):
        """Test para validad que se llenen los campos en hr.employee dependiendo de las cuentas bancarias del contacto"""
        # sin cuentas bancarias
        self.partner.bank_ids = False
        self.employee._compute_select_information_partner()
        self._create_asserts(self.employee)

        # con cuentas bancarias de tipo sueldo
        self.partner.bank_ids = [(0, 0, {
            'bank_id': self.bank.id,
            'acc_number': '1912454696111',
            'cci': '00219100245469611751',
            'acc_type': 'wage', # tipo sueldo
        }),]
        self.employee._compute_select_information_partner()
        self._create_asserts(self.employee, '1912454696111', 'BCP')

        # con cuentas bancarias de tipo cts
        self.partner.bank_ids = False
        self.partner.bank_ids = [(0, 0, {
            'bank_id': self.bank.id,
            'acc_number': '0987654321',
            'cci': '00219100245469611751',
            'acc_type': 'cts',
        }),]
        self.employee._compute_select_information_partner()
        self._create_asserts(self.employee, '', '', '0987654321', 'BCP')

        print("<<<<<<<<<< TEST 3 PASSED >>>>>>>>>>")
