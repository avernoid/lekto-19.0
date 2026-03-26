from odoo import fields, models

class AccountMove(models.Model):
    _inherit = 'account.move'

    mobilvendor_id = fields.Char(
        string="Mobilvendor ID",
        help="ID of the invoice from the external system",
        index=True
    )
    mobilvendor_route_definition = fields.Char(
        string="Mobilvendor Route",
        help="Route name assigned in Mobilvendor",
        index=True,
        readonly=True
    )
    mobilvendor_vendor_id = fields.Many2one(
        'hr.employee',
        string="Mobilvendor Vendor",
        help="Employee assigned directly via ID from Mobilvendor",
        readonly=True
    )
    mobilvendor_route_id = fields.Many2one(
        'mobilvendor.route',
        string='Sales Route',
        index=True
    )

    def action_check_mobilvendor_status(self):
        """
        Consulta el estado de la factura en Mobilvendor. 
        Si está anulada (estado 3), ejecuta la desconciliación de pagos, 
        anulación de la factura y reversión del inventario (Devolución).
        """
        self.ensure_one()
        from odoo.exceptions import UserError
        import logging
        _logger = logging.getLogger(__name__)

        if not self.mobilvendor_id:
            raise UserError("Esta factura no tiene un ID de Mobilvendor asociado.")

        company = self.env.company
        if not company.mobilvendor_api_url:
            raise UserError("La compañía no tiene configurada la integración con Mobilvendor.")

        # Instanciar el API handler
        from ..services.mobilvendor_api import MobilvendorAPIHandler
        api_handler = MobilvendorAPIHandler(company=company, env=self.env)

        # Consultar la factura específica. Asumimos que la API permite filtrar por ID o lo traemos del lote del día.
        # Para evitar traer datos masivos, acotamos la búsqueda a la fecha de la factura.
        start_date = self.invoice_date.strftime('%Y-%m-%d') if self.invoice_date else ''
        filter_invoice = {
            "id": self.mobilvendor_id,  # Intentamos filtro directo
            "start_date": start_date
        }

        try:
            invoices_response = api_handler._send_get_request(action="getInvoices", filter=filter_invoice)
        except Exception as e:
            raise UserError(f"Error al comunicarse con Mobilvendor: {str(e)}")

        if "headers" not in invoices_response:
            # Si el filtro por ID falló y trajo todo, o no existe, manejamos el caso
            raise UserError("Respuesta inválida de Mobilvendor al consultar la factura.")

        invoice_headers = api_handler._process_invoice_headers(invoices_response.get("headers"))
        
        # Buscar la factura en la respuesta (por si la API ignoró el filtro 'id' y trajo varias)
        mv_invoice_data = invoice_headers.get(self.mobilvendor_id)

        if not mv_invoice_data:
            raise UserError(f"No se encontró la factura {self.mobilvendor_id} en Mobilvendor para la fecha consultada.")

        status = mv_invoice_data.get('status')

        if status != '3':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': "Estado en Mobilvendor",
                    'message': f"La factura está en estado normal (Status: {status}). No requiere anulación.",
                    'type': 'info',
                    'sticky': False,
                }
            }

        # --- REVERSAL LOGIC (Tomada de _process_cancelled_invoices_page) ---
        if self.state == 'cancel':
            raise UserError("La factura ya se encuentra anulada en Odoo.")

        _logger.info(f"Iniciando anulación manual desde botón para factura {self.name} (MV ID: {self.mobilvendor_id})")

        # 1. Unreconcile Payments
        for payment in self.payment_ids:
            try:
                reconciled_invoice_line = self.line_ids.filtered(
                    lambda x: x.account_id.account_type in ('asset_receivable')
                )
                reconciled_payment_line = payment.move_id.line_ids.filtered(
                    lambda x: x.account_id.account_type in ('asset_receivable')
                )
                all_reconciled_lines = reconciled_invoice_line + reconciled_payment_line
                if all_reconciled_lines:
                    all_reconciled_lines.remove_move_reconcile()
            except Exception as e:
                _logger.error(f"Error unreconciling payment for invoice {self.mobilvendor_id}: {str(e)}")

        # 2. Cancel Payments
        for payment in self.payment_ids:
            try:
                if payment.state == 'posted':
                    payment.action_draft()
                payment.action_cancel()
            except Exception as e:
                _logger.error(f"Error canceling payment for invoice {self.mobilvendor_id}: {str(e)}")

        # 3. Cancel Invoice
        try:
            if self.state == 'posted':
                self.button_cancel()
        except Exception as e:
            raise UserError(f"No se pudo anular la factura en Odoo: {str(e)}")

        # 4. Reverse Stock Movements
        related_stock_moves = self.env['stock.move'].search([('mobilvendor_id', '=', self.mobilvendor_id)])
        for move in related_stock_moves:
            picking = move.picking_id
            if picking and picking.state == 'done':
                try:
                    # Crear Contexto/Wizard de devolución
                    # Utilizamos odoo stock.return.picking
                    ReturnPicking = self.env['stock.return.picking'].with_context(
                        active_ids=picking.ids, active_id=picking.id).create({})
                    
                    return_action = ReturnPicking.create_returns()
                    new_picking_id = return_action.get('res_id')
                    
                    if new_picking_id:
                        new_picking = self.env['stock.picking'].browse(new_picking_id)
                        new_picking.action_confirm()
                        # Completar el movimiento de retorno inmediatamente si es necesario
                        # _logger.info(f"Created return picking {new_picking.name}")
                except Exception as e:
                    _logger.error(f"Error reversing stock for picking {picking.name}: {str(e)}")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "Sincronización de Anulación",
                'message': "La factura estaba anulada en Mobilvendor. Se han cancelado los pagos, la factura, y se generaron los movimientos de devolución de inventario.",
                'type': 'success',
                'sticky': False,
            }
        }
