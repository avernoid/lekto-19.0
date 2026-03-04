from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from datetime import datetime, timedelta


@tagged('post_install', '-at_install')
class TestAbsenceDay(TransactionCase):

    def setUp(self):
        super(TestAbsenceDay, self).setUp()
        # Crear datos básicos para las pruebas
        self.work_entry_type_leave = self.env['hr.work.entry.type'].create({
            'name': 'Test Leave',
            'code': 'TEST_LEAVE',
        })
        
        self.work_entry_type_holiday = self.env['hr.work.entry.type'].create({
            'name': 'Test Holiday',
            'code': 'TEST_HOLIDAY',
        })

        # Crear un calendario de recursos
        self.calendar = self.env['resource.calendar'].create({
            'name': 'Test Calendar',
            'hours_per_day': 8,
            'attendance_ids': [
                (0, 0, {
                    'name': 'Monday Morning',
                    'dayofweek': '0',
                    'hour_from': 8,
                    'hour_to': 12,
                }),
                (0, 0, {
                    'name': 'Monday Afternoon',
                    'dayofweek': '0',
                    'hour_from': 13,
                    'hour_to': 17,
                }),
            ],
        })

    def test_01_create_global_time_off(self):
        """Test creación de una ausencia global"""
        date_from = datetime.now()
        date_to = date_from + timedelta(days=1)
        
        global_leave = self.env['resource.calendar.leaves'].create({
            'name': 'Test Global Leave',
            'date_from': date_from,
            'date_to': date_to,
            'calendar_id': self.calendar.id,
            'work_entry_type_id': self.work_entry_type_leave.id,
        })
        
        self.assertTrue(global_leave, "La ausencia global no se creó correctamente")
        self.assertEqual(global_leave.name, 'Test Global Leave', 
                        "El nombre de la ausencia global no coincide")
        self.assertEqual(global_leave.work_entry_type_id, self.work_entry_type_leave,
                        "El tipo de entrada de trabajo no coincide")

        print("<<<<<<<<<< TEST 1 PASSED >>>>>>>>>>")

    def test_02_verify_calendar_global_leaves(self):
        """Test verificación de ausencias globales en el calendario"""
        # Crear múltiples ausencias globales
        date_from = datetime.now()
        leaves_data = [
            {
                'name': 'Holiday 1',
                'date_from': date_from,
                'date_to': date_from + timedelta(days=1),
                'work_entry_type_id': self.work_entry_type_holiday.id
            },
            {
                'name': 'Holiday 2',
                'date_from': date_from + timedelta(days=7),
                'date_to': date_from + timedelta(days=8),
                'work_entry_type_id': self.work_entry_type_holiday.id
            }
        ]
        
        for leave_data in leaves_data:
            self.calendar.global_leave_ids = [(0, 0, leave_data)]
        
        self.assertEqual(len(self.calendar.global_leave_ids), 2,
                        "No se crearon correctamente todas las ausencias globales")
        
        print("<<<<<<<<<< TEST 2 PASSED >>>>>>>>>>")

    def test_03_verify_work_entry_types(self):
        """Test verificación de tipos de entrada de trabajo"""
        work_entry_types = self.env['hr.work.entry.type'].search([
            ('code', 'in', ['TEST_LEAVE', 'TEST_HOLIDAY'])
        ])
        
        self.assertEqual(len(work_entry_types), 2,
                        "No se encontraron todos los tipos de entrada de trabajo")
        
        codes = work_entry_types.mapped('code')
        self.assertIn('TEST_LEAVE', codes,
                     "No se encontró el tipo de entrada TEST_LEAVE")
        self.assertIn('TEST_HOLIDAY', codes,
                     "No se encontró el tipo de entrada TEST_HOLIDAY")

        print("<<<<<<<<<< TEST 3 PASSED >>>>>>>>>>")

    def test_04_verify_form_view(self):
        """Test verificación de la vista de formulario"""
        form_view = self.env.ref('absence_day.resource_calendar_form_view_inherit_absence_day')
        self.assertTrue(form_view, "No se encontró la vista de formulario")
        
        # Verificar que la vista hereda correctamente
        self.assertEqual(form_view.inherit_id.model, 'resource.calendar',
                        "La vista no hereda del modelo correcto")
        
        # Verificar que la vista contiene los campos necesarios
        arch = form_view.arch
        self.assertIn('global_leave_ids', arch,
                     "No se encontró el campo global_leave_ids en la vista")
        self.assertIn('work_entry_type_id', arch,
                     "No se encontró el campo work_entry_type_id en la vista")

        print("<<<<<<<<<< TEST 4 PASSED >>>>>>>>>>")