from odoo.tests import Form
from odoo.tests import common
from datetime import date

@common.tagged('post_install', '-at_install')
class TestPaymentConditionsContract(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.payment_period = self.env['payment.period'].create({
            'code': '11',
            'payment_description': 'Descripcion Semestral',
            'name': 'Prueba Semestral'
        })
        self.payment_type = self.env['payment.type'].create({
            'code': '12',
            'payment_description': 'Pago en Cuenta',
            'name': 'Cuenta'
        })
        self.special_situation = self.env['special.situation'].create({
            'code': '13',
            'situation_description': 'Trabajo Remoto',
            'name': 'Trabajo Remoto'
        })

        self.variable_payment = self.env['variable.payment'].create({
            'code': '14',
            'name': 'Pago variable'
        })
        self.structure_type = self.env['hr.payroll.structure.type'].search([])
        self.employee = self.env['hr.employee'].search([])
        
        self.specific_structure = self.env['hr.payroll.structure'].create({
            'name': 'End of the Year Bonus - Test',
            'schedule_pay_conditions': self.payment_period.id,
            'type_id': self.structure_type[0].id
        })
        
        self.contract = self.env['hr.version'].create({
            'name': 'Contract',
            'employee_id': self.employee[0].id,
            'wage': 1,
            'date_version': date(2023, 1, 1),
            'hr_responsible_id': self.env.user.id,
            'special_situation_id': self.special_situation.id,
            'payment_type_id': self.payment_type.id,
            'variable_payment_id': self.variable_payment.id,
            'structure_type_id': self.structure_type[0].id,
        })

    def test_create_contract(self):
        self.assertEqual(self.contract.name, 'Contract')
        self.assertEqual(self.contract.employee_id.id, self.employee[0].id)
        self.assertEqual(self.contract.wage, 1)
        self.assertEqual(self.contract.date_version, date(2023, 1, 1))
        self.assertEqual(self.contract.special_situation_id.id, self.special_situation.id)
        self.assertEqual(self.contract.payment_type_id.id, self.payment_type.id)
        self.assertEqual(self.contract.variable_payment_id.id, self.variable_payment.id)
        self.assertEqual(self.contract.structure_type_id.id, self.structure_type[0].id)
    
    def test_create_payment_period(self):
        self.assertEqual(self.payment_period.code, '11')
        self.assertEqual(self.payment_period.payment_description, 'Descripcion Semestral')
        self.assertEqual(self.payment_period.name, 'Prueba Semestral')

    def test_create_payment_type(self):
        self.assertEqual(self.payment_type.code, '12')
        self.assertEqual(self.payment_type.payment_description, 'Pago en Cuenta')
        self.assertEqual(self.payment_type.name, 'Cuenta')

    def test_create_special_situation(self):
        self.assertEqual(self.special_situation.code, '13')
        self.assertEqual(self.special_situation.situation_description, 'Trabajo Remoto')
        self.assertEqual(self.special_situation.name, 'Trabajo Remoto')

    def test_create_variable_payment(self):
        self.assertEqual(self.variable_payment.code, '14')
        self.assertEqual(self.variable_payment.name, 'Pago variable')
        
        

