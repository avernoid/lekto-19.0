from odoo import models, fields, api
from math import fabs
from dateutil.relativedelta import relativedelta
from datetime import timedelta


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    service_hire_date = fields.Date(
        string='Fecha de Contratación',
        groups='hr.group_hr_user',
        compute='_compute_service_hire_date', 
        inverse='_inverse_service_hire_date',
        store=True,
        readonly=False,  # Permite editar el campo aunque sea computed
        help=(
            'Fecha de contratación es normalmente la fecha en que un empleado completa'
            ' la documentación de nueva contratación'
        ),
    )
    service_start_date = fields.Date(
        string='Fecha de Inicio',
        groups='hr.group_hr_user',
        help=(
            'Fecha de inicio es el primer día que el empleado trabaja y'
            ' esta fecha se usa para el cálculo de asignaciones de vacaciones'
        ),
    )
    service_termination_date = fields.Date(
        string='Fecha de Cese',
        groups='hr.group_hr_user',
        help=(
            'Fecha de cese es el último día que el empleado trabaja y'
            ' esta fecha se usa para el cálculo de asignaciones de vacaciones'
        ),
    )
    service_duration = fields.Integer(
        string='Duración del Servicio',
        groups='hr.group_hr_user',
        compute='_compute_service_duration',
        help='Duración del servicio en días',
        store=True
    )
    service_duration_years = fields.Integer(
        string='Duración del Servicio (años)',
        groups='hr.group_hr_user',
        compute='_compute_service_duration',
        store=True
    )
    service_duration_months = fields.Integer(
        string='Duración del Servicio (meses)',
        groups='hr.group_hr_user',
        compute='_compute_service_duration',
        store=True
    )
    service_duration_days = fields.Integer(
        string='Duración del Servicio (días)',
        groups='hr.group_hr_user',
        compute='_compute_service_duration',
        store=True
    )

    @api.depends('service_start_date', 'contract_date_end')
    def _compute_service_duration(self):
        for record in self:
            if hasattr(record, 'contract_date_end') and record.contract_date_end:
                if record.contract_date_end >= fields.Date.today():
                    service_until = fields.Date.today()
                else:
                    service_until = record.contract_date_end
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
    
    def _inverse_service_hire_date(self):
        """
        Permite que el campo sea editable manualmente
        """
        # No hacemos nada aquí, solo permitimos que el valor se guarde
        pass

    @api.onchange('service_hire_date')
    def _onchange_service_hire_date(self):
        """
        Si service_start_date está vacío, copia automáticamente service_hire_date.
        """
        for record in self:
            if record.service_hire_date and not record.service_start_date:
                record.service_start_date = record.service_hire_date
