from odoo import api, fields, models


class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    def _get_duration_is_valid(self):
        return False


class HrEmployee(models.Model):
    _inherit = 'hr.employee'


    no_provide_pension = fields.Boolean(
        string='Does not contribute pension',
        help='If checked, indicates that the employee does not contribute to a pension fund.',
        default=False,
        groups='hr.group_hr_user')

    l10n_pe_microenterprise_manager = fields.Boolean(
        string='Conductor Micro',
        help='El ingreso remunerativo de este empleado, será considerado como INGRESO CONDUCTOR DE MICROEMPRESA en el PLAME',
        groups="hr.group_hr_user"
    )

    def _check_no_apply_afp_premium(self):
        return True if self.age >= 65.0 and not self.indicator else False

    no_apply_afp_premium = fields.Boolean(
        string='Does not apply AFP premium',
        help='Automatically checked if the employee is over 65 years old, avoiding AFP premium deduction.',
        default=lambda self: self._check_no_apply_afp_premium(),
        groups='hr.group_hr_user'
    )
    indicator = fields.Boolean(default=False, help='Technical field used to indicate if the AFP premium exemption condition has been met.', groups='hr.group_hr_user')

    upper = fields.Char(compute='_compute_upper',
                        inverse='_inverse_upper',
                        search='_search_upper')

    @api.onchange('age')
    def _compute_onchange_no_apply_afp_premium(self):
        for rec in self:
            if rec.age >= 65.0 and not rec.indicator:
                rec.no_apply_afp_premium = True
                rec.indicator = True

    def _inverse_no_apply_afp_premium(self):
        pass
    

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def get_order_periods(self, periods):
        """
        :param periods: list of periods with this string format: mm/YYYY
        :return: list of ordered periods
        """
        new_periods = []
        for period in periods:
            _, last_day = self.env['hr.payslip'].get_month_day_range(period)
            new_periods.append(last_day)
        new_periods.sort()
        periods = [val.strftime('%m/%Y') for val in new_periods]
        return periods

    def _get_base_local_dict(self):
        """
        Pass hr.payslip id to specific searches in computed rule
        """

        res = super()._get_base_local_dict()
        res.update({
            'slip_id': self._origin.id
        })
        return res

    @staticmethod
    def _get_month(year, month, value_month):
        value = month - value_month
        if value < 0:
            new_month = 12 + value
            new_year = year - 1
        elif value == 0:
            new_month = 12
            new_year = year - 1
        else:
            new_month = value
            new_year = year
        return new_month, new_year

    def _get_periods(self, start_m, start_y, end_m, end_y):
        periods = self.env['hr.payslip.line']._get_periods(start_m, start_y, end_m, end_y)
        return periods

    def _get_months_before(self, months_before):
        month = int(self.month)
        year = int(self.year)
        start_m, star_y = self._get_month(year, month, months_before)
        end_m, end_y = self._get_month(year, month, 1)
        periods = self._get_periods(start_m, star_y, end_m, end_y)
        return periods

    @staticmethod
    def get_month_day_range(period):
        """
        :param period: month with format : mm/YYYY => Ex: 06/20
        :return: Return initial and final date of some period
        """
        datetime_str = '{}-{}-01 15:00:00'.format(period[3:], period[0:2])
        datetime_object = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S').date()
        last_day = datetime_object + relativedelta(day=1, months=+1, days=-1)
        first_day = datetime_object + relativedelta(day=1)
        return first_day, last_day