from odoo import api, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)

def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    cr.execute("""
        UPDATE account_move
        SET bool_pay_invoice = TRUE
        WHERE bool_pay_invoice IS NULL
          AND bool_pay_invoice_tmp ~* '^\\s*CANCELAD[OA]\\.?(\\s*)$';
    """)

    cr.execute("ALTER TABLE account_move DROP COLUMN IF EXISTS bool_pay_invoice_tmp;")
    _logger.info("Se elimino columna temporal bool_pay_invoice_tmp de la tabla account_move")