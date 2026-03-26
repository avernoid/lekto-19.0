# -*- coding: utf-8 -*-
from datetime import datetime
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

from ..services.mobilvendor_api import MobilvendorAPIHandler
from ..utils.credentials_manager import encrypt_credential

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    mobilvendor_api_username = fields.Char(string="Usuario", help="Username for mobilvendor API")
    mobilvendor_api_password = fields.Char(string="Clave", help="Password for mobilvendor API")
    mobilvendor_api_url = fields.Char(string="API URL", help="URL for mobilvendor API")
    mobilvendor_api_context = fields.Char(string="Contexto", help="Context for mobilvendor API")
    mobilvendor_api_session_id = fields.Char(string="API Session ID", help="Session ID for mobilvendor API")
    mobilvendor_api_days_sync = fields.Integer(string="Días de sincronización",
                                               help="Number of days for sync with Mobilvendor")
    mobilvendor_api_conciliate_credit_notes = fields.Boolean(
        string="Activar Conciliación autom. (NC)",
        default=False,
        help="Controla el cruce contable cuando Mobilvendor envía una Nota de Crédito (NC).\n"
             "Si está MARCADO: La NC entrante buscará automáticamente la factura que le dio origen en Odoo y ejecutará una conciliación matemática inmediata. El saldo del cliente disminuirá sin intervención manual.\n"
             "Si está DESMARCADO: La NC se creará y validará, pero quedará 'abierta'. El equipo contable deberá ingresar a la factura original y conciliar manualmente la NC contra el saldo pendiente."
    )

    mobilvendor_invoice_journal_id = fields.Many2one(
        'account.journal',
        string="Invoice Journal ID"
    )
    mobilvendor_payment_journal_id = fields.Many2one(
        'account.journal',
        string="Payment Journal ID"
    )

    # Flag to control password visibility in the form
    show_password = fields.Boolean(string="Mostrar contraseña", default=False)

    # Aux fields for button visibility — computed from show_password (not stored)
    show_edit_button = fields.Boolean(compute="_compute_button_visibility", store=False)
    show_save_button = fields.Boolean(compute="_compute_button_visibility", store=False)

    @api.depends("show_password")
    def _compute_button_visibility(self):
        for rec in self:
            rec.show_edit_button = not bool(rec.show_password)
            rec.show_save_button = bool(rec.show_password)

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to encrypt credentials"""
        for vals in vals_list:
            if vals.get('mobilvendor_api_password'):
                vals['mobilvendor_api_password'] = encrypt_credential(
                    vals['mobilvendor_api_password']
                )
        return super(ResCompany, self).create(vals_list)

    def write(self, vals):
        """Encrypt the password before saving when updating."""
        if 'mobilvendor_api_password' in vals and vals.get('mobilvendor_api_password'):
            try:
                vals['mobilvendor_api_password'] = encrypt_credential(vals['mobilvendor_api_password'])
            except Exception as e:
                _logger.exception("Error encrypting mobilvendor_api_password on write: %s", e)
                # Optionally raise or continue; here we continue with original value
        return super(ResCompany, self).write(vals)

    def show_password_hide(self):
        """
        Toggle visibility to show the password (this method name is as in your XML).
        In your XML: 'Editar Credenciales' will call this to enable editing (show_password True).
        """
        for rec in self:
            rec.write({'show_password': True})
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def show_password_show(self):
        """
        Toggle visibility to hide the password (this method name is as in your XML).
        In your XML: 'Guardar Credenciales' will call this to save and hide (show_password False).
        """
        for rec in self:
            rec.write({'show_password': False})
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    @api.model
    def action_open_mobilvendor(self):
        """
        Opens the form view for the current company (Mobilvendor credentials).
        Ensures show_password is False when opening.
        """
        company = self.env.company

        if not company:
            raise UserError(_("Company not found."))

        # Reset the show_password flag to False for existing record
        try:
            company.write({'show_password': False})
        except Exception:
            # fallback if write fails for any reason
            company.show_password = False

        return {
            'type': 'ir.actions.act_window',
            'name': _('API Credentials'),
            'res_model': 'res.company',
            'res_id': company.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'show_password': company.show_password},
        }

    # --------------------------
    # Synchronization helpers
    # --------------------------
    def _ensure_company_for_sync(self):
        company = self.env.company
        if not company:
            raise UserError(_("Company not found."))
        return company

    def sync_inventory(self):
        company = self._ensure_company_for_sync()
        api_handler = MobilvendorAPIHandler(company=company, env=self.env)
        return api_handler.sync_inventory()

    def sync_customers_users(self):
        company = self._ensure_company_for_sync()
        api_handler = MobilvendorAPIHandler(company=company, env=self.env)
        return api_handler.sync_customers_users()

    def sync_invoice_and_payments(self):
        company = self._ensure_company_for_sync()
        api_handler = MobilvendorAPIHandler(company=company, env=self.env)
        return api_handler.sync_fast_invoices_payments()

    def sync_all(self):
        company = self._ensure_company_for_sync()
        api_handler = MobilvendorAPIHandler(company=company, env=self.env)
        return api_handler.sync_all()

    def sync_price_list_products(self):
        company = self._ensure_company_for_sync()
        api_handler = MobilvendorAPIHandler(company=company, env=self.env)
        return api_handler.sync_price_list_products()
