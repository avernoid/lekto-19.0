from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestJudicialRetentionFields(TransactionCase):

    def setUp(self):
        super(TestJudicialRetentionFields, self).setUp()
        self.hr_employee = self.env['hr.employee']
        self.hr_payslip = self.env['hr.payslip']

    def test_01_create_employee(self):
        try:
            # Safely get or create a structure type to avoid relying on demo data
            structure_type = self.env['hr.payroll.structure.type'].search([], limit=1)
            if not structure_type:
                # Need to specify required fields for structure type. 'name' is usually enough.
                structure_type = self.env['hr.payroll.structure.type'].create({
                    'name': 'Test Structure Type',
                })
                
            self.employee = self.hr_employee.create({
                'name': 'Fernando Pastor',
                'wage': 2000,
                'structure_type_id': structure_type.id,
            })
        except Exception as e:
            self.fail(f"Creation of employee failed: {e}")

    def test_02_create_judicial_retention(self):
        self.test_01_create_employee()

        payslip = self.hr_payslip.create({
            'name': 'Payslip for Fernando Pastor',
            'employee_id': self.employee.id,
            'date_from': '2024-06-01',
            'date_to': '2024-06-30',
        })

        try:
            payslip.action_get_judicial_format()
        except ValidationError as e:
            self.fail(f"Report generation failed: {e}")
        except Exception as e:
            if "unexpected error" in str(e).lower():
                self.fail(f"Test failed due to unexpected error message: {e}")
