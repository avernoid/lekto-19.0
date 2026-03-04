from datetime import datetime

from odoo.tests import common


class TestPartnerConcept(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({
            'name': 'Partner de Prueba',
        })
        self.structure_type = self.env['hr.payroll.structure.type'].create({
            'name': 'Tipo de estructura de prueba',
        })
        self.work_entry_type = self.env['hr.work.entry.type'].create({
            'name': 'Tipo de entrada de prueba',
            'is_leave': True,
            'code': 'LEAVETEST300',
            'round_days': 'HALF',
            'round_days_type': 'DOWN',
        })
        self.structure = self.env['hr.payroll.structure'].create({
            'name': 'Estructura de prueba',
            'type_id': self.structure_type.id,
            'unpaid_work_entry_type_ids': [(4, self.work_entry_type.id, False)]
        })
        self.salary_rule = self.env['hr.salary.rule'].create({
            'name': 'Regla Salarial de Prueba',
            'sequence': 5,
            'amount_select': 'percentage',
            'amount_percentage': 40.0,
            'amount_percentage_base': 'contract.wage',
            'code': 'HRA',
            'category_id': self.env.ref('hr_payroll.ALW').id,
            'struct_id': self.structure.id,
        })
        self.partner_concept = self.env['hr.partner.concept'].create({
            'partner_id': self.partner.id,
            'salary_rule_id': self.salary_rule.id,
            'amount': 1000.0,
            'percentage': 5.0,
            'is_debit': True,
            'is_credit': False,
            'is_active': True,
            'start_date': '2023-01-01',
            'end_date': '2023-12-31',
        })
        self.employee = self.env['hr.employee'].create({
            'name': 'Empleado de Prueba',
        })

    def test_partner_concept_creation(self):
        self.assertTrue(
            self.partner_concept.partner_id,
            'Socio de Prueba no configurado correctamente'
        )
        self.assertTrue(
            self.partner_concept.salary_rule_id,
            'Regla Salarial de Prueba no configurada correctamente'
        )
        self.assertEqual(
            self.partner_concept.amount,
            1000.0,
            'Importe no configurado correctamente'
        )
        self.assertEqual(
            self.partner_concept.percentage,
            5.0,
            'Porcentaje no configurado correctamente'
        )
        self.assertTrue(
            self.partner_concept.is_debit,
            'Es débito? no configurado correctamente'
        )
        self.assertFalse(
            self.partner_concept.is_credit,
            'Es Crédito? no configurado correctamente'
        )
        self.assertTrue(
            self.partner_concept.is_active,
            'Está activo? no configurado correctamente'
        )
        self.assertEqual(
            self.partner_concept.start_date,
            datetime.strptime('2023-01-01', '%Y-%m-%d').date(),
            'Fecha de Inicio no configurada correctamente'
        )
        self.assertEqual(
            self.partner_concept.end_date,
            datetime.strptime('2023-12-31', '%Y-%m-%d').date(),
            'Fecha de Fin no configurada correctamente'
        )
        print("---- TEST 1 ----")

    def test_employee_with_salary_concept(self):
        self.employee.partner_concept_ids = [(4, self.partner_concept.id)]
        self.assertEqual(
            len(self.employee.partner_concept_ids),
            1,
            'Concepto de Socio no añadido correctamente'
        )
        print("---- TEST 2 ----")
