import datetime

from odoo.tests.common import TransactionCase


class TestPayslipFields(TransactionCase):
    """Tests for the computed payroll-month fields added by payroll_field."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Payslip = cls.env['hr.payslip']
        cls.PayslipRun = cls.env['hr.payslip.run']

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------
    def _compute_month(self, date_from, date_to):
        """Call the standalone helper and return (date_start, year, month, date_start_dt)."""
        return self.Payslip.generate_date_start_month_year(date_from, date_to)

    # ------------------------------------------------------------------
    # Tests – compute logic on hr.payslip
    # ------------------------------------------------------------------
    def test_00_single_month_range(self):
        """When from/to fall in the same month, that month is selected."""
        date_from = datetime.date(2025, 3, 1)
        date_to = datetime.date(2025, 3, 31)
        date_start, year, month, dt = self._compute_month(date_from, date_to)
        self.assertEqual(date_start, '03/2025')
        self.assertEqual(year, '2025')
        self.assertEqual(month, '03')
        self.assertEqual(dt, date_to)

    def test_01_cross_month_majority_first(self):
        """When the range spans two months and more days fall in the first, pick first."""
        # 20 Jan – 5 Feb  →  Jan has more days
        date_from = datetime.date(2025, 1, 20)
        date_to = datetime.date(2025, 2, 5)
        date_start, year, month, dt = self._compute_month(date_from, date_to)
        self.assertEqual(month, '01')
        self.assertEqual(year, '2025')

    def test_02_cross_month_majority_second(self):
        """When the range spans two months and more days fall in the second, pick second."""
        # 28 Jan – 28 Feb  →  Feb has more days
        date_from = datetime.date(2025, 1, 28)
        date_to = datetime.date(2025, 2, 28)
        date_start, year, month, dt = self._compute_month(date_from, date_to)
        self.assertEqual(month, '02')
        self.assertEqual(year, '2025')

    # ------------------------------------------------------------------
    # Tests – compute logic on hr.payslip.run (batch)
    # ------------------------------------------------------------------
    def test_03_batch_date_st_dt(self):
        """Batch date_st_dt is computed from date_start / date_end."""
        batch = self.PayslipRun.create({
            'name': 'Test Batch',
            'date_start': datetime.date(2025, 6, 1),
            'date_end': datetime.date(2025, 6, 30),
        })
        self.assertEqual(batch.date_st_dt, datetime.date(2025, 6, 30))

    def test_04_batch_cross_month(self):
        """Batch date_st_dt picks the correct month across boundaries."""
        batch = self.PayslipRun.create({
            'name': 'Cross-month Batch',
            'date_start': datetime.date(2025, 8, 25),
            'date_end': datetime.date(2025, 9, 24),
        })
        # Sep has more days (24) vs Aug (6+1=7 from 25-31)
        self.assertEqual(batch.date_st_dt.month, 9)
