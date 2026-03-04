import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Copia service_start_date → vacation_start_date para todos los empleados
    que tengan has_holidays = True y vacation_start_date aún vacío.
    Esto preserva el comportamiento anterior del Generador de Vacaciones
    para instalaciones ya existentes.
    """
    if not version:
        return

    cr.execute("""
        UPDATE hr_employee
        SET vacation_start_date = service_start_date
        WHERE has_holidays = TRUE
          AND vacation_start_date IS NULL
          AND service_start_date IS NOT NULL
    """)
    _logger.info(
        "holiday_process migration: vacation_start_date populated from service_start_date "
        "for %d employees.", cr.rowcount
    )
