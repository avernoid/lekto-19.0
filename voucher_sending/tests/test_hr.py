from odoo.tests.common import TransactionCase
from odoo.tools.misc import format_date

class TestHr(TransactionCase):
        
    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        user_admin = self.env.ref("base.user_admin")
        self.env = self.env(user=user_admin)
        self.HrPayslip = self.env["hr.payslip"]     
        self.employee = self.env["hr.employee"].create({
            "name": "name1",    
        })
        
        self.hr_payslip1 = self.HrPayslip.create({
            "employee_mail": False,
            "employee_id": self.employee.id,
            "status": "signed",
            "name": "testName"
        })
        
        print("--------------------SETUP DONE---------------------------")
        
    def test_fields_values_hr(self):
        self.assertFalse(self.hr_payslip1.employee_mail, False)
        self.assertEqual(self.hr_payslip1.employee_id.id, self.employee.id)
        self.assertEqual(self.hr_payslip1.status, "signed")
        self.assertEqual(self.hr_payslip1.name, "testName")
        print("----------------------TEST FIELDS VALUES DONE-----------------------")
        
    
    def test_get_report_base_filename(self):
        filename = self.hr_payslip1._get_report_base_filename()
        self.assertEqual(filename, 'Payslip - testName')
        print("----------------------TEST GET REPORT BASE FILENAME DONE-----------------------") 
    
    def test_compute_display_name(self):
        self.hr_payslip1._compute_display_name()

        lang = self.hr_payslip1.employee_id.sudo().address_id.lang or self.env.user.lang
        display_name = 'Boleta de pago - %s' % format_date(self.env, self.hr_payslip1.date_from, date_format="MMMM y", lang_code=lang)

        self.assertEqual(self.hr_payslip1.display_name, display_name)

        print("----------------------TEST COMPUTE DISPLAY NAME DONE-----------------------")
    
           
