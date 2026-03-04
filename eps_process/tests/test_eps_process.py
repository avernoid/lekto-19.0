from datetime import datetime

from odoo.tests import common

@common.tagged('post_install', '-at_install')
class TestEpsProcess(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.eps_credit = self.env['eps.credit'].create({
            'since': datetime(2023, 1, 1),
            'until': datetime(2023, 1, 31),
            'affiliated_workers': 1,
            'computable_remuneration_health_input':3.5,
            'eps_credit':50,
            'eps_service_cost':2.4,
            'uit':3.1,
            'uit_limit_affiliated_workers':1.5,
            'adjustment':1.2,
            'final_eps_credit':2.3
        })
        self.partner_id= self.env['res.partner'].create({
            'name': 'Partner EPS Test',
        })
        self.eps_management = self.env['eps.management'].create({
            'star_date': datetime(2023, 1, 1),
            'finish_date': datetime(2023, 1, 31),
            'entity':'Entidad',
            'partner_id': self.partner_id.id,
            'insurance': '43242323',
            'rate_employer':3.5,
            'amount_employer':2.5,
            'rate_worker':1.5,
            'amount_worker': 2.4,
            '_writing_employees':False,
        })
        self.employee = self.env['hr.employee'].create({
            'name': 'Empleado de Prueba',
            'exists_eps':True,
            'management_eps':self.eps_management.id,
        })
        self.hr_employee_relative_relation = self.env['hr.employee.relative.relation'].create({
            'name': 'HR EMPLOYEE RELATION DE PRUEBA',
        })
        self.hr_employee_relative = self.env['hr.employee.relative'].create({
            'name': 'HR EMPLOYEE RELATIVE',
            'percentage_eps': 50,
            'tax_eps': 35,
            'payer_eps': True,
            'disability':False,
            'max_age':90,
            'relation_id':self.hr_employee_relative_relation.id,
        })
    
    def test_fields_eps_credit(self):
        self.assertEqual(self.eps_credit.since,datetime(2023, 1, 1).date())
        self.assertEqual(self.eps_credit.until,datetime(2023, 1, 31).date())
        self.assertEqual(self.eps_credit.affiliated_workers,1)
        self.assertEqual(self.eps_credit.computable_remuneration_health_input,3.5)
        self.assertEqual(self.eps_credit.eps_credit,50)
        self.assertEqual(self.eps_credit.eps_service_cost,2.4)
        self.assertEqual(self.eps_credit.uit,3.1)
        self.assertEqual(self.eps_credit.uit_limit_affiliated_workers,1.5)
        self.assertEqual(self.eps_credit.adjustment,1.2)
        self.assertEqual(self.eps_credit.final_eps_credit,2.3)
        
        print("-----------TEST FIELDS EPS CREDIT OK-----------")
        
    def test_fields_eps_management(self):
        self.assertEqual(self.eps_management.display_name,'Entidad-43242323')
        self.assertEqual(self.eps_management.star_date,datetime(2023, 1, 1).date())
        self.assertEqual(self.eps_management.finish_date,datetime(2023, 1, 31).date())
        self.assertEqual(self.eps_management.entity,'Entidad')
        self.assertEqual(self.eps_management.insurance,'43242323')
        self.assertEqual(self.eps_management.partner_id.id,self.partner_id.id)
        self.assertEqual(self.eps_management.rate_employer,3.5)
        self.assertEqual(self.eps_management.amount_employer,2.5)
        self.assertEqual(self.eps_management.rate_worker,1.5)
        self.assertEqual(self.eps_management.amount_worker,2.4)
        self.assertEqual(self.eps_management._writing_employees,False)
        
        print("-----------TEST FIELDS EPS MANAGEMENT OK-----------")
        
    def test_fields_hr_employee_relative(self):
        self.assertEqual(self.hr_employee_relative.name,'HR EMPLOYEE RELATIVE')
        self.assertEqual(self.hr_employee_relative.percentage_eps,50)
        self.assertEqual(self.hr_employee_relative.tax_eps,35)
        self.assertEqual(self.hr_employee_relative.payer_eps,True)
        self.assertEqual(self.hr_employee_relative.disability,False)
        self.assertEqual(self.hr_employee_relative.max_age,90)
        self.assertEqual(self.hr_employee_relative.relation_id.id,self.hr_employee_relative_relation.id)
        
        print("-----------TEST FIELDS HR EMPLOYEE RELATIVE OK-----------")
        
    def test_employee_with_eps_management(self):
        self.eps_management.employeer_ids = [(4, self.employee.id, False)]
        self.assertEqual(
            len(self.eps_management.employeer_ids),
            1,
            'Empleado no añadido correctamente'
        )
    

