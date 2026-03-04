from odoo.tests.common import TransactionCase

class TestVariousData(TransactionCase):
    def setUp(self):
        super(TestVariousData, self).setUp()

    def test_create_sctr(self):
        sctr = self.env['various.data.sctr'].create({
            'register_date': '2022-01-01',
            'due_date': '2022-12-31',
            'pension_percent': 10.0,
            'health_percent': 5.0,
            'pension_amount': 1000.0,
            'health_amount': 500.0,
            'sctr_name': 'Entidad de Prueba SCTR',
            'name_id': 2,
        })
        self.assertEqual(sctr.sctr_name, 'Entidad de Prueba SCTR')
        self.assertEqual(sctr.pension_percent, 10.0)
        self.assertEqual(sctr.health_percent, 5.0)
        self.assertEqual(sctr.pension_amount, 1000.0)
        self.assertEqual(sctr.health_amount, 500.0)
        print("---- Test test_create_sctr OK ---")

    def test_create_uit(self):
        uit = self.env['various.data.uit'].create({
            'register_date': '2022-01-01',
            'due_date': '2022-12-31',
            'uit_amount': 3500.0,
            'is_active': True,
        })
        self.assertEqual(uit.uit_amount, 3500.0)
        self.assertTrue(uit.is_active)
        print("---- Test test_create_uit OK ---")

    def test_create_sis(self):
        sis = self.env['various.data.sis'].create({
            'register_date': '2022-01-01',
            'due_date': '2022-12-31',
            'sis_amount': 1000.0,
            'is_active': True,
        })
        self.assertEqual(sis.sis_amount, 1000.0)
        self.assertTrue(sis.is_active)
        print("---- Test test_create_sis OK ---")

    def test_create_rmv(self):
        various_data_rmv = self.env['various.data.rmv'].create({
            'register_date': '2023-01-01',
            'due_date': '2023-12-31',
            'rmv_amount': 1000,
            'af_amount': 100,
            'is_active': True,
        })
        self.assertTrue(various_data_rmv)
        self.assertTrue(various_data_rmv.is_active)
        print("---- Test test_create_rmv OK ---")

    def test_compute_rmv_total(self):
        various_data_rmv = self.env['various.data.rmv'].create({
            'register_date': '2023-01-01',
            'due_date': '2023-12-31',
            'rmv_amount': 1200,
            'af_amount': 100,
            'is_active': True,
        })

        rmv_total = various_data_rmv.rmv_amount +various_data_rmv.af_amount
        self.assertEqual(rmv_total, 1300)
        print("---- Test test_compute_rmv_total OK ---")

