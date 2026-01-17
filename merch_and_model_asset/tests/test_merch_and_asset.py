from freezegun import freeze_time
from odoo.tests.common import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo import fields


@freeze_time('2022-06-30')
@tagged('post_install', '-at_install')
class TestAssets(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_depreciation_expense = cls.company_data['default_account_assets'].copy()
        cls.asset_counterpart_account_id = cls.company_data['default_account_expense'].copy()
        cls.degressive_asset = cls.create_asset(
            value=7200,
            periodicity="monthly",
            periods=60,
            method="degressive",
            method_progress_factor=0.35,
            acquisition_date="2020-07-01",
            prorata="constant_periods"
        )
        cls.degressive_then_linear_asset = cls.create_asset(
            value=7200,
            periodicity="monthly",
            periods=60,
            method="degressive_then_linear",
            method_progress_factor=0.35,
            acquisition_date="2020-07-01",
            prorata="constant_periods"
        )

    @classmethod
    def create_asset(cls, value, periodicity, periods, import_depreciation=0, acquisition_date="2022-02-01", prorata='none', **kwargs):
        return cls.env['account.asset'].create({
            'name': 'nice asset',
            'account_asset_id': cls.company_data['default_account_assets'].id,
            'account_depreciation_id': cls.account_depreciation_expense.id,
            'account_depreciation_expense_id': cls.company_data['default_account_expense'].id,
            'journal_id': cls.company_data['default_journal_misc'].id,
            'acquisition_date': acquisition_date,
            'prorata_computation_type': prorata,
            'original_value': value,
            'salvage_value': 0,
            'method_number': periods,
            'method_period': '12' if periodicity == "yearly" else '1',
            'method': "linear",
            'asset_brand': 'Marca prueba',
            'asset_model': 'Modelo Prueba',
            'asset_series': 'Serie de prueba',
            'already_depreciated_amount_import': import_depreciation,
            **kwargs,
        })

    @classmethod
    def _get_depreciation_move_values(cls, date, depreciation_value, remaining_value, depreciated_value, state):
        return {
            'date': fields.Date.from_string(date),
            'depreciation_value': depreciation_value,
            'asset_remaining_value': remaining_value,
            'asset_depreciated_value': depreciated_value,
            'state': state,
        }

    def test_new_fields_in_asset(self):
        asset = self.create_asset(value=7200, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-02-01", prorata="constant_periods")
        asset.validate()
        self.assertEqual(asset.asset_brand, 'Marca prueba', 'La marca del activo no es la esperada')
        self.assertEqual(asset.asset_model, 'Modelo Prueba', 'El modelo del activo no es el esperado')
        self.assertEqual(asset.asset_series, 'Serie de prueba', 'El número de serie del activo no es el esperado')
        print('---------------------Test new fields in asset passed-----------------------')

    def test_linear_start_beginning_month_reevaluation_beginning_month(self):
        asset = self.create_asset(value=7200, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-02-01", prorata="constant_periods")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date': fields.Date.to_date("2022-06-01"),
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=600, remaining_value=6600, depreciated_value=600, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=600, remaining_value=6000, depreciated_value=1200, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=600, remaining_value=5400, depreciated_value=1800, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=600, remaining_value=4800, depreciated_value=2400, state='posted'),
            # 20 because we have 1 * 600 / 30 (1 day of a month of 30 days, with 600 per month)
            self._get_depreciation_move_values(date='2022-06-01', depreciation_value=20, remaining_value=4780, depreciated_value=2420, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=580, remaining_value=4200, depreciated_value=3000, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=600, remaining_value=3600, depreciated_value=3600, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=600, remaining_value=3000, depreciated_value=4200, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=600, remaining_value=2400, depreciated_value=4800, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=600, remaining_value=1800, depreciated_value=5400, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=600, remaining_value=1200, depreciated_value=6000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=600, remaining_value=600, depreciated_value=6600, state='draft'),
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=600, remaining_value=0, depreciated_value=7200, state='draft'),
        ])
        print('---------------------Test linear start beginning month reevaluation beginning month passed-----------------------')
