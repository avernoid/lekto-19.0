from odoo import models, fields, api
from math import fabs
from dateutil.relativedelta import relativedelta
from datetime import timedelta


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    service_hire_date = fields.Date(
        string='Hire Date',
        groups='hr.group_hr_user',
        compute='_compute_service_hire_date',
        help=(
            'The date the employee was originally hired. This field is automatically '
            'calculated based on the oldest active contract version found in the system.'
        ),
    )
    service_start_date = fields.Date(
        string='Start Date',
        groups='hr.group_hr_user',
        help=(
            'The actual first day the employee started working. This date is critical '
            'for calculating accrual leave allocations and benefits.'
        ),
    )
    service_termination_date = fields.Date(
        string='Termination Date',
        groups='hr.group_hr_user',
        help=(
            'The last day the employee worked. If set, the service duration calculation '
            'will stop accumulating at this date.'
        ),
    )
    service_duration = fields.Integer(
        string='Service Duration',
        groups='hr.group_hr_user',
        compute='_compute_service_duration',
        help='Service duration in days',
        store=True
    )
    service_duration_years = fields.Integer(
        string='Service Duration (years)',
        groups='hr.group_hr_user',
        compute='_compute_service_duration',
        store=True
    )
    service_duration_months = fields.Integer(
        string='Service Duration (months)',
        groups='hr.group_hr_user',
        compute='_compute_service_duration',
        store=True
    )
    service_duration_days = fields.Integer(
        string='Service Duration (days)',
        groups='hr.group_hr_user',
        compute='_compute_service_duration',
        store=True
    )

    @api.depends('service_start_date', 'service_termination_date')
    def _compute_service_duration(self):
        for record in self:
            if hasattr(record, 'service_termination_date') and record.service_termination_date:
                if record.service_termination_date >= fields.Date.today():
                    service_until = fields.Date.today()
                else:
                    service_until = record.service_termination_date
            else:
                service_until = fields.Date.today()

            if record.service_start_date and service_until > record.service_start_date:
                service_since = record.service_start_date
                service_duration = fabs((service_until - service_since) / timedelta(days=1))
                record.service_duration = int(service_duration)
                service_duration = relativedelta(service_until, record.service_start_date)
                record.service_duration_years = service_duration.years
                record.service_duration_months = service_duration.months
                record.service_duration_days = service_duration.days
            else:
                record.service_duration = 0
                record.service_duration_years = 0
                record.service_duration_months = 0
                record.service_duration_days = 0

    @api.onchange('service_hire_date')
    def _onchange_service_hire_date(self):
        if not self.service_start_date:
            self.service_start_date = self.service_hire_date

    @api.depends('version_ids', 'version_ids.active', 'version_ids.date_start')
    def _compute_service_hire_date(self):
        """
        Calcula service_hire_date basándose en la versión de contrato más antigua
        que no esté cancelada ni archivada.
        """
        for record in self:
            if not record.version_ids:
                record.service_hire_date = False
                continue
                
            # Filtrar versiones válidas: no canceladas y no archivadas
            valid_versions = record.version_ids.filtered(
                lambda v: v.active
            )
            
            if valid_versions:
                # Ordenar por fecha de inicio y tomar la más antigua
                oldest_version = valid_versions.sorted(
                    key=lambda v: v.date_start
                )[0]
                record.service_hire_date = oldest_version.date_start
            else:
                record.service_hire_date = False
    

    
    def _get_date_start_work(self):
        return self.service_start_date or super()._get_date_start_work()
