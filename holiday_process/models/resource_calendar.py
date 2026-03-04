import math
from collections import defaultdict
from datetime import datetime, timedelta

import pytz
from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, WEEKLY, rrule
from pytz import timezone

from odoo import models
from odoo.addons.resource.models.resource_calendar import Intervals,float_to_time

from odoo.osv import expression


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    def _get_resources_day_total(self, from_datetime, to_datetime, resources=None):
        """
        @devuelve diccionario con horas de asistencia en cada día entre `from_datetime` y `to_datetime`
        """
        self.ensure_one()
        resources = self.env['resource.resource'] if not resources else resources
        resources_list = list(resources) + [self.env['resource.resource']]
        # total hours per day:  recupera asistencias con un margen de día adicional,
        # para calcular el total de horas en el primer y último día
        from_full = from_datetime - timedelta(days=1)
        to_full = to_datetime + timedelta(days=1)

        if self.env.context.get('holiday_status_id', False):
            intervals = self.with_context(holiday_status_id=True)._attendance_intervals_batch(from_full, to_full, resources=resources)
        else:
            intervals = self._attendance_intervals_batch(from_full, to_full, resources=resources)

        result = defaultdict(lambda: defaultdict(float))
        for resource in resources_list:
            day_total = result[resource.id]
            for start, stop, meta in intervals[resource.id]:
                day_total[start.date()] += (stop - start).total_seconds() / 3600
        return result
    

    def _attendance_intervals_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None, lunch=False):
        """ Devuelve los intervalos de asistencia en el rango de fecha y hora dado,
            usando solo los campos válidos del calendario de recursos.
        """
        self.ensure_one()
        resources = self.env['resource.resource'].search([]) if not resources else resources
        assert start_dt.tzinfo and end_dt.tzinfo
        combine = datetime.combine
        resources_list = [r for r in resources if r.id]

        domain = domain if domain is not None else []
        domain = expression.AND([domain, [
            ('calendar_id', '=', self.id),
            ('display_type', '=', False),
            ('day_period', '!=' if not lunch else '=', 'lunch'),
        ]])

        cache_dates = defaultdict(dict)
        cache_deltas = defaultdict(dict)
        result = defaultdict(list)

        attendance_model = self.env['resource.calendar.attendance']
        attendance_ids = attendance_model.search(domain)

        for attendance in attendance_ids:
            for resource in resources_list:
                resource_tz = tz or pytz.timezone(getattr(resource, 'tz', 'UTC'))

                start_utc = start_dt.astimezone(pytz.utc)
                end_utc = end_dt.astimezone(pytz.utc)

                start_date = start_dt.date()
                until_date = end_dt.date()

                weekday = int(attendance.dayofweek)
                if getattr(self, 'two_weeks_calendar', False) and attendance.week_type:
                    days = rrule(WEEKLY, dtstart=start_date, until=until_date, byweekday=weekday, interval=2)
                else:
                    days = rrule(DAILY, dtstart=start_date, until=until_date, byweekday=weekday)

                for day in days:
                    hour_from = attendance.hour_from
                    dt0 = cache_deltas.get((resource_tz, day, hour_from))
                    if not dt0:
                        dt0 = resource_tz.localize(combine(day, float_to_time(hour_from)))
                        cache_deltas[(resource_tz, day, hour_from)] = dt0

                    hour_to = attendance.hour_to
                    dt1 = cache_deltas.get((resource_tz, day, hour_to))
                    if not dt1:
                        dt1 = resource_tz.localize(combine(day, float_to_time(hour_to)))
                        cache_deltas[(resource_tz, day, hour_to)] = dt1

                    dt0_utc = dt0.astimezone(pytz.utc)
                    dt1_utc = dt1.astimezone(pytz.utc)

                    interval_start = max(start_utc, dt0_utc)
                    interval_end = min(end_utc, dt1_utc)
                    if interval_start < interval_end:
                        result[resource.id].append((interval_start, interval_end, attendance))

        return {r.id: Intervals(result.get(r.id, [])) for r in resources_list}
