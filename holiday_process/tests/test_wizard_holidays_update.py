from odoo.tests import common

class TestHolidaysUpdateWizard(common.TransactionCase):
    def setUp(self):
        super(TestHolidaysUpdateWizard, self).setUp()
        self.update_wizard = self.env['holiday.update.wizard'].create({'date': '2023-06-26'})

    def test_action_generate_holidays(self):
        self.update_wizard.action_generate_holidays()
     

    def test_recalculate_holidays_per_new_interval(self):
  
        employee1 = self.env['hr.employee'].create({
            'name': 'Empleado 1',
            'holidays_per_year': 24,
        })
        employee2 = self.env['hr.employee'].create({
            'name': 'Empleado 2',
            'holidays_per_year': 30,
        })

        self.update_wizard._recalculate_holidays_per_new_interval()


 

      

    
