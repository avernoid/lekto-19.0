from datetime import datetime

from dateutil.relativedelta import relativedelta
from odoo.tests import Form, common
from odoo.exceptions import ValidationError


@common.tagged('post_install', '-at_install')
class TestHrEmployeeRelatives(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.relation_sibling = cls.env.ref('personal_information.relation_sibling')
        cls.partner_1 = cls.env['res.partner'].create({'name': 'Marco Vasquez'})
        cls.partner_2 = cls.env['res.partner'].create({'name': 'Arturo Jesus'})

    def setUp(self):
        super().setUp()
        self.employee = self.env['hr.employee'].create({
            'name': 'Leo Daniel Flores Sánchez',
            'relative_ids': [(0, 0, {
                'relation_id': self.relation_sibling.id,
                'partner_id': self.partner_1.id,
                'name': 'Marco Vasquez',
                'sex': 'male',
                'phone_number': '+51 982367182',
                'job': 'Ingeniero de Software',
                'notes': 'Esta es una nota :D',
                'date_of_birth': datetime.now() - relativedelta(years=28),
            })]
        })
        self.employee_relative = self.env['hr.employee.relative'].browse(self.employee.relative_ids[0].id)

    def test_age_calculation(self):
        """Test age calculation for employee relatives."""
        self.assertEqual(self.employee_relative.age, 28)

        new_date_of_birth = datetime.now() - relativedelta(years=45)
        self.employee_relative.write({'date_of_birth': new_date_of_birth})
        self.assertEqual(self.employee_relative.age, 45)

    def test_sync_relatives(self):
        """Test synchronization of children count and spouse info."""
        # Clean existing relatives
        self.employee.relative_ids.unlink()
        
        # Create Child 1
        child_relation = self.env.ref('personal_information.relation_child')
        self.env['hr.employee.relative'].create({
            'employee_id': self.employee.id,
            'relation_id': child_relation.id,
            'name': 'Hijo 1',
            'date_of_birth': datetime.now() - relativedelta(years=5),
        })
        # Force recompute/flush
        self.employee.invalidate_recordset()
        self.assertEqual(self.employee.children, 1, "Children count should be 1")

        # Create Child 2
        self.env['hr.employee.relative'].create({
            'employee_id': self.employee.id,
            'relation_id': child_relation.id,
            'name': 'Hijo 2',
            'date_of_birth': datetime.now() - relativedelta(years=3),
        })
        self.employee.invalidate_recordset()
        self.assertEqual(self.employee.children, 2, "Children count should be 2")

        # Create Spouse
        spouse_relation = self.env.ref('personal_information.relation_spouse')
        spouse_dob = datetime.now() - relativedelta(years=30)
        self.env['hr.employee.relative'].create({
            'employee_id': self.employee.id,
            'relation_id': spouse_relation.id,
            'name': 'Esposa Test',
            'date_of_birth': spouse_dob,
        })
        self.employee.invalidate_recordset()
        self.assertEqual(self.employee.spouse_complete_name, 'Esposa Test')
        self.assertEqual(self.employee.spouse_birthdate, spouse_dob.date())

    def test_validations(self):
        """Test birthdate and unique spouse validations."""
        spouse_relation = self.env.ref('personal_information.relation_spouse')
        
        # 1. Future Birthdate
        with self.assertRaises(ValidationError, msg="Should not allow future birthdate"):
            self.env['hr.employee.relative'].create({
                'employee_id': self.employee.id,
                'relation_id': spouse_relation.id,
                'name': 'Future Baby',
                'date_of_birth': datetime.now() + relativedelta(days=1),
            })

        # 2. Unique Spouse
        # Ensure one spouse exists (from setUp or create new if not)
        # In setUp we created a Sibling. Let's create a Spouse first.
        self.employee.relative_ids.unlink()
        self.env['hr.employee.relative'].create({
            'employee_id': self.employee.id,
            'relation_id': spouse_relation.id,
            'name': 'Esposa 1',
            'date_of_birth': datetime.now() - relativedelta(years=30),
        })

        # Try to create *another* spouse
        with self.assertRaises(ValidationError, msg="Should not allow second spouse"):
            self.env['hr.employee.relative'].create({
                'employee_id': self.employee.id,
                'relation_id': spouse_relation.id,
                'name': 'Esposa 2',
                'date_of_birth': datetime.now() - relativedelta(years=25),
            })


    def test_legal_name_and_capitalization(self):
        """Test auto-capitalization and legal name generation."""
        # Enable Legal Name generation for current company
        self.env.company.generate_legal_name = True

        with Form(self.employee) as f:
            f.firstname = 'juan'
            f.lastname = 'perez'
            f.secondname = 'lopez'
        
        # Verify Capitalization
        self.assertEqual(self.employee.firstname, 'Juan')
        self.assertEqual(self.employee.lastname, 'Perez')
        self.assertEqual(self.employee.secondname, 'Lopez')

        # Verify Legal Name Auto-Gen
        self.assertEqual(self.employee.legal_name, 'Juan Perez Lopez')

        # Disable setting and verify NO update
        self.env.company.generate_legal_name = False
        with Form(self.employee) as f:
            f.firstname = 'PEDRO' # Should still title-case
        
        self.assertEqual(self.employee.firstname, 'Pedro')
        # Legal name should REMAIN 'Juan Perez Lopez' because sync is off
        self.assertEqual(self.employee.legal_name, 'Juan Perez Lopez')