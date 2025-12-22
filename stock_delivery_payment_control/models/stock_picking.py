from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    payment_coverage_status = fields.Selection(
        [
            ('no_control', 'No Control'),
            ('not_covered', 'Not Covered'),
            ('partially_covered', 'Partially Covered'),
            ('fully_covered', 'Fully Covered'),
            ('credit_not_due', 'Credit Not Due')
        ],
        string="Payment Coverage",
        compute='_compute_payment_coverage_status',
        store=True,
        help="Payment status relative to the items in this picking"
    )

    @api.depends('picking_type_id.enforce_payment_control', 'sale_id', 'move_ids.sale_line_id', 'sale_id.invoice_ids.payment_state', 'sale_id.order_line.qty_invoiced', 'sale_id.picking_ids.state', 'sale_id.picking_ids.move_ids.quantity')
    def _compute_payment_coverage_status(self):
        for picking in self:
            # Only control pickings where the picking type enforces it.
            # This allows flexible configuration for multi-step routes.
            if not picking.picking_type_id.enforce_payment_control:
                 picking.payment_coverage_status = 'no_control'
                 continue

            if not picking.sale_id:
                picking.payment_coverage_status = 'no_control'
                continue

            # Determine effective policy to check if we even need to calculate
            # (Optimization: though requirement says "Always show status", so we calculate regardless of policy active state usually, 
            # but usually status is relevant when control is active. 
            # Requirement: "Ambos modelos SIEMPRE muestran estado de cobranza")
            # So we calculate always if there is a sale_id.

            # Gather sale lines involved in this picking
            sale_lines = picking.move_ids.mapped('sale_line_id')
            if not sale_lines:
                # Could be a picking without sale lines (e.g. extra moves), fallback to sale status or no_control
                picking.payment_coverage_status = picking.sale_id.payment_coverage_status if picking.sale_id else 'no_control'
                continue

            # Calculate coverage for these specific lines
            # We need to see if the quantity delivered in THIS picking (or attempted to be delivered) is covered by invoices/payments.
            # This is complex because invoices are not directly linked to picking lines easily 1:1 without digging.
            # Simplified approach based on "Proportion invoiced and paid"
            
            # Helper to check line status
            total_needed_value = 0.0
            total_paid_value = 0.0
            
            # We assume the value of the picking is the sum of (qty_in_picking * unit_price)
            # And we check how much of that is covered by paid invoices.
            
            # However, mapping specific payments to specific lines is impossible in standard Odoo core.
            # We must rely on the aggregate status of the lines.
            
            # Logic:
            # 1. Total value of this picking = sum(move.product_uom_qty * line.price_unit)
            # 2. Check if the SALE LINES are invoiced.
            # 3. Check if those Invoices are paid.
            
            all_lines_fully_invoiced = True
            any_line_paid = False
            total_picking_value = 0
            
            for move in picking.move_ids:
                if not move.sale_line_id: 
                    continue
                line = move.sale_line_id
                
                # Value of this move
                move_val = move.product_uom_qty * line.price_unit
                total_picking_value += move_val
                
                # Check invoicing status of the line
                # qty_invoiced vs qty_to_invoice vs qty_delivered...
                # If we are validating, we use quantity_done if set, otherwise product_uom_qty? 
                # "Cantidades del picking" -> usually means what we are moving now.
                
                # Simplification: Is the *amount* covered by *any* paid invoice on the order?
                # This might be too loose.
                
                # Let's look at the requirement: "Análisis por línea de sale.order"
                # "Proporción facturada y pagada"
                
                pass

            # Alternative robust logic:
            # Calculate % of the Sale Order that this picking represents.
            # Calculate % of the Sale Order that is paid.
            # If %paid >= %picking_cumulative_delivered (including this one), then covered.
            
            # But the requirement implies we might pay *specifically* for this picking (e.g. Cash on Delivery or Prepay for specific goods).
            # If standard Odoo, we just have a pool of payments on the SO.
            
            # Going with "Global Sale Coverage" appproach restricted to the lines?
            # Let's stick to the Sale Order's payment status for simplicity if "picking" level isn't strictly needing per-line payment matching (which doesn't exist).
            # WAIT. Requirement 4B: "El estado se calcula en base a... Cantidades del picking... Líneas de sale.order asociadas"
            
            # Implementation:
            # Calculate the monetary value of the items in this picking.
            picking_value = sum(m.product_uom_qty * m.sale_line_id.price_unit for m in picking.move_ids if m.sale_line_id)
            
            # Calculate the total value of the SO
            so_total = picking.sale_id.amount_total
            
            # Calculate total paid amount on SO
            so_paid = 0.0
            for inv in picking.sale_id.invoice_ids:
                if inv.state == 'posted':
                    so_paid += (inv.amount_total - inv.amount_residual)
            
            # If we are "Credit Not Due", we consider it covered for validation purposes, but status is specific.
            # "credit_not_due es un estado positivo (no bloqueante)"
            
            # Check Credit
            is_credit = False
            if picking.sale_id.include_credit_analysis and picking.sale_id.payment_term_id:
                 if any(line.nb_days > 0 for line in picking.sale_id.payment_term_id.line_ids):
                    is_credit = True
            
            # Status Logic
            # If so_paid >= picking_value (plus previously delivered? No, "Cantidades del picking")
            # Usually we want enough payment to cover *cumulative* deliveries or just *this* one?
            # Standard logic: Prepay means I pay X, I get X worth of goods.
            # If I delivered 1000 worth before, and I deliver 500 now. I need 1500 paid total?
            # OR just 500 for this one?
            # Assuming CUMULATIVE integrity: Total Paid >= Total Delivered (incl. this one).
            
            # Calculate value of ALL validation/done pickings + this one
            # Note: This is complex because "this one" is not yet done.
            # And other pickings might be done.
            
            # Let's try a simpler per-picking check as per prompt "based on ... amounts of the picking".
            # If (Total Paid on Order - Value of ALREADY Delivered Goods) >= Value of THIS Picking.
            
            # Delivered value so far (excluding this picking if it's not done):
            # IMPORTANT: Filter by 'enforce_payment_control' to avoid double counting in multi-step routes
            # Only pickings that are marked as control points count as "Value Delivered" to the customer.
            delivered_moves = picking.sale_id.picking_ids.filtered(lambda p: p.state == 'done' and p.id != picking.id and p.picking_type_id.enforce_payment_control).move_ids
            delivered_value = sum(m.product_uom_qty * m.sale_line_id.price_unit for m in delivered_moves if m.sale_line_id)
            
            available_payment = so_paid - delivered_value
            
            if available_payment >= picking_value and picking_value > 0:
                picking.payment_coverage_status = 'fully_covered'
            elif available_payment > 0:
                picking.payment_coverage_status = 'partially_covered'
            else:
                 # If value is 0 (free items?), covered.
                if picking_value == 0:
                     picking.payment_coverage_status = 'fully_covered'
                elif is_credit:
                    picking.payment_coverage_status = 'credit_not_due'
                else:
                    picking.payment_coverage_status = 'not_covered'


    def button_validate(self):
        # Intercept action
        for picking in self:
            if not picking.sale_id or not picking.picking_type_id.enforce_payment_control:
                continue

            # Determine Policy
            policy_active = False
            validation_level = 'sale' # default
            req_full = False
            
            if picking.sale_id.payment_control_active:
                policy_active = True
                validation_level = picking.sale_id.payment_validation_level
                req_full = picking.sale_id.require_full_payment
            elif picking.picking_type_id.payment_control_active:
                policy_active = True
                validation_level = picking.picking_type_id.payment_validation_level
                req_full = picking.picking_type_id.require_full_payment
            
            if not policy_active:
                continue

            # Force recompute of payment coverage status to ensure it's up to date with other pickings' status
            # This handles the case where another sibling picking was just validated.
            picking._compute_payment_coverage_status()

            # Check Status
            status = 'no_control'
            if validation_level == 'sale':
                status = picking.sale_id.payment_coverage_status
            else:
                status = picking.payment_coverage_status
            
            # Evaluate Block
            if status == 'no_control':
                continue
            if status == 'credit_not_due':
                continue
            if status == 'fully_covered':
                continue
            
            if status == 'not_covered':
                raise UserError(_("Blocking Validation: Payment not covered (Status: %s)") % status)
            
            if status == 'partially_covered':
                if req_full:
                    raise UserError(_("Blocking Validation: Partial payment not allowed (Full Payment Required)"))
                # else allow

        return super().button_validate()
