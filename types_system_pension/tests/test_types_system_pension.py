import logging
from odoo.tests import common
from datetime import datetime

_logger = logging.getLogger(__name__)


@common.tagged('post_install', '-at_install')
class TestTypeSystemPension(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.tope_afp = self.env['tope.afp'].create({
            'date_from': datetime(2024, 1, 1),
            'date_to': datetime(2024, 1, 31),
            'top': 1179614
        })
        self.pension_system = self.env['pension.system'].create({
            'code': 'code prueba',
            'pension_system': 'regimen prueba',
            'name': 'abreviatura',
            'private_sector': True,
            'public_sector': True,
            'other_entities': True,
            'cuspp': True,
            'comis_pension_ids': False
        })
        self.comis_pension = self.env['comis.system.pension'].create({
            'date_from': datetime(2021, 1, 4),
            'date_to': datetime(2021, 1, 5),
            'fund': 4,
            'bonus': 5,
            'mixed_flow': 7,
            'flow': 8,
            'balance': 9,
            'pension_id': self.pension_system.id
        })

        self.user_without_image = self.env['res.users'].create({
            'name': 'Marc Demo',
            'email': 'mark.brown23@example.com',
            'image_1920': False,
            'login': 'demo_1',
            'password': 'demo_123'
        })
        self.employee_without_image = self.env['hr.employee'].create({
            'user_id': self.user_without_image.id,
            'image_1920': False,
            'cuspp': 'cuspp 2',
            'is_cuspp': True,
            'pension_system_id': self.pension_system.id,
            'pension_sctr': True,
            'commission_type': 'amount'
        })

    def test_fields_pension(self):
        name = '[%s - %s] %s' % (self.tope_afp.date_from or '', self.tope_afp.date_to or '', self.tope_afp.top)
        self.assertEqual(self.tope_afp.display_name,name)
        self.assertEqual(self.pension_system.code, 'code prueba')
        self.assertEqual(self.pension_system.pension_system, 'regimen prueba')
        self.assertEqual(self.pension_system.name, 'abreviatura')
        self.assertTrue(self.pension_system.private_sector)
        self.assertTrue(self.pension_system.public_sector)
        self.assertTrue(self.pension_system.other_entities)
        self.assertTrue(self.pension_system.cuspp)
        _logger.info("-----------TEST FIELDS PENSION OK-----------")

    def test_fields_comis(self): 
        self.assertEqual(self.comis_pension.date_from, datetime(2021, 1, 4).date())
        self.assertEqual(self.comis_pension.date_to, datetime(2021, 1, 5).date())
        self.assertEqual(self.comis_pension.fund, 4)
        self.assertEqual(self.comis_pension.bonus, 5)
        self.assertEqual(self.comis_pension.mixed_flow, 7)
        self.assertEqual(self.comis_pension.flow, 8)
        self.assertEqual(self.comis_pension.balance, 9)
        self.assertEqual(self.comis_pension.pension_id.id, self.pension_system.id)
        _logger.info("-----------TEST FIELDS COMIS OK-----------")

    def test_employee_linked_partner(self):
        user_partner = self.user_without_image.partner_id
        work_contact = self.employee_without_image.work_contact_id
        self.assertEqual(user_partner, work_contact)
        _logger.info('------TEST ADDITIONAL VOUCHER FIELDS OK--------------')
