from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Elimina el FK constraint huerfano de github_partner_id.

    En versiones anteriores, github_partner_id era Many2one (integer FK).
    Al cambiarse a fields.Char, la columna quedo como varchar en la BD
    pero el constraint de FK no fue eliminado automaticamente, causando
    un DatatypeMismatch al intentar actualizar el modulo.
    """
    if not version:
        return

    cr.execute("""
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'github_sales_access'
          AND constraint_name = 'github_sales_access_github_partner_id_fkey'
          AND constraint_type = 'FOREIGN KEY'
    """)
    if cr.fetchone():
        _logger.info(
            'Migration: dropping obsolete FK constraint '
            'github_sales_access_github_partner_id_fkey'
        )
        cr.execute(
            'ALTER TABLE github_sales_access '
            'DROP CONSTRAINT github_sales_access_github_partner_id_fkey'
        )
    else:
        _logger.info(
            'Migration: FK constraint github_sales_access_github_partner_id_fkey '
            'not found, nothing to drop.'
        )
