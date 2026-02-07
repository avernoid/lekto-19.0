from odoo import api
import logging

_logger = logging.getLogger(__name__)

def migrate(cr, version):

    cr.execute("SELECT data_type FROM information_schema.columns WHERE table_name='account_move' AND column_name='bool_pay_invoice'")
    (data_type,) = cr.fetchone()

    cr.execute("ALTER TABLE account_move ADD COLUMN IF NOT EXISTS bool_pay_invoice_tmp TEXT;")
    cr.execute("UPDATE account_move SET bool_pay_invoice_tmp = bool_pay_invoice::text WHERE bool_pay_invoice_tmp IS NULL")
    _logger.info("Se creó columna temporal bool_pay_invoice_tmp y se copiaron los datos")

    if data_type != 'boolean':
        cr.execute("""
            ALTER TABLE account_move
            ALTER COLUMN bool_pay_invoice
            TYPE boolean
            USING CASE
              WHEN trim(both from upper(regexp_replace(bool_pay_invoice_tmp, '\\.$', '')))
                   IN ('CANCELADO','CANCELADA') THEN TRUE
              WHEN bool_pay_invoice_tmp IS NULL OR btrim(bool_pay_invoice_tmp) = '' THEN NULL
              ELSE NULL
            END;
        """)
        _logger.info("bool_pay_invoice convertido a Boolean desde el respaldo")
    else:
        _logger.info("bool_pay_invoice ya era Boolean: no se altera el tipo")