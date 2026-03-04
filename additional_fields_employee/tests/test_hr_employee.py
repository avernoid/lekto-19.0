# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAdditionalFieldsEmployee(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Master data records
        cls.academic_degree = cls.env['academic.degree'].create({
            'code': '10',
            'academic_description': 'Complete University',
            'name': 'UNIV',
        })
        cls.health_regime = cls.env['health.regime'].create({
            'code': '01',
            'health_description': 'EsSalud Regular',
            'name': 'ESS',
        })
        cls.employee_regime = cls.env['employee.regime'].create({
            'code': '01',
            'regime_description': 'General Private Regime',
            'name': 'GPR',
            'private_sector': True,
            'public_sector': False,
            'other_entities': False,
            'is_mype': False,
        })
        cls.type_contract = cls.env['type.contract'].create({
            'code': '01',
            'contract_type': 'Indefinite',
            'name': 'IND',
        })
        cls.work_occupation = cls.env['work.occupation'].create({
            'code': '01',
            'name': 'Employee',
            'executive': False,
            'employee': True,
            'worker': False,
        })
        # Employee
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
        })

    # ----------------------------------------------------------------
    # 1. Master Data CRUD
    # ----------------------------------------------------------------
    def test_master_data_academic_degree(self):
        """academic.degree records persist correctly."""
        self.assertEqual(self.academic_degree.code, '10')
        self.assertEqual(self.academic_degree.academic_description, 'Complete University')
        self.assertEqual(self.academic_degree.name, 'UNIV')

    def test_master_data_health_regime(self):
        """health.regime records persist correctly."""
        self.assertEqual(self.health_regime.code, '01')
        self.assertEqual(self.health_regime.health_description, 'EsSalud Regular')

    def test_master_data_employee_regime(self):
        """employee.regime records persist with boolean flags."""
        self.assertTrue(self.employee_regime.private_sector)
        self.assertFalse(self.employee_regime.public_sector)
        self.assertFalse(self.employee_regime.is_mype)

    def test_master_data_type_contract(self):
        """type.contract records persist correctly."""
        self.assertEqual(self.type_contract.code, '01')
        self.assertEqual(self.type_contract.contract_type, 'Indefinite')

    def test_master_data_work_occupation(self):
        """work.occupation records persist with category flags."""
        self.assertFalse(self.work_occupation.executive)
        self.assertTrue(self.work_occupation.employee)
        self.assertFalse(self.work_occupation.worker)

    # ----------------------------------------------------------------
    # 2. hr.version fields
    # ----------------------------------------------------------------
    def test_hr_version_many2one_fields(self):
        """Many2one fields on hr.version persist correctly."""
        version = self.employee.version_id
        version.write({
            'academic_degree_id': self.academic_degree.id,
            'health_regime_id': self.health_regime.id,
            'labor_regime_id': self.employee_regime.id,
            'labor_condition_id': self.type_contract.id,
            'work_occupation_id': self.work_occupation.id,
        })
        self.assertEqual(version.academic_degree_id, self.academic_degree)
        self.assertEqual(version.health_regime_id, self.health_regime)
        self.assertEqual(version.labor_regime_id, self.employee_regime)
        self.assertEqual(version.labor_condition_id, self.type_contract)
        self.assertEqual(version.work_occupation_id, self.work_occupation)

    def test_hr_version_boolean_fields(self):
        """Boolean labor flags on hr.version persist correctly."""
        version = self.employee.version_id
        version.write({
            'maximum_working_day': True,
            'atypical_cumulative_day': False,
            'nocturnal_schedule': True,
            'unionized': False,
            'is_practitioner': True,
        })
        self.assertTrue(version.maximum_working_day)
        self.assertFalse(version.atypical_cumulative_day)
        self.assertTrue(version.nocturnal_schedule)
        self.assertFalse(version.unionized)
        self.assertTrue(version.is_practitioner)

    # ----------------------------------------------------------------
    # 3. Employee inherited field propagation
    # ----------------------------------------------------------------
    def test_employee_inherited_many2one_propagation(self):
        """Writing Many2one fields on hr.employee propagates to version_id."""
        self.employee.write({
            'academic_degree_id': self.academic_degree.id,
            'health_regime_id': self.health_regime.id,
            'labor_regime_id': self.employee_regime.id,
            'labor_condition_id': self.type_contract.id,
            'work_occupation_id': self.work_occupation.id,
        })
        version = self.employee.version_id
        self.assertEqual(version.academic_degree_id, self.academic_degree)
        self.assertEqual(version.health_regime_id, self.health_regime)
        self.assertEqual(version.labor_regime_id, self.employee_regime)
        self.assertEqual(version.labor_condition_id, self.type_contract)
        self.assertEqual(version.work_occupation_id, self.work_occupation)

    def test_employee_inherited_boolean_propagation(self):
        """Writing boolean flags on hr.employee propagates to version_id."""
        self.employee.write({
            'maximum_working_day': True,
            'nocturnal_schedule': True,
            'unionized': True,
            'is_practitioner': False,
            'atypical_cumulative_day': True,
        })
        version = self.employee.version_id
        self.assertTrue(version.maximum_working_day)
        self.assertTrue(version.nocturnal_schedule)
        self.assertTrue(version.unionized)
        self.assertFalse(version.is_practitioner)
        self.assertTrue(version.atypical_cumulative_day)
