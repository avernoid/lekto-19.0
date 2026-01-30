from odoo import models, api, fields
import datetime
import logging
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare

_logger = logging.getLogger(__name__)

class StockMove(models.Model):
    _inherit = "stock.move"

    def _recalculate_valuation_waterfall(self, product_id, start_date, initial_qty, initial_value, new_standard_price=None):
        """
        Core algorithm to recalculate AVCO from a specific point in time.
        """
        product = self.env['product.product'].browse(product_id)
        
        if product.cost_method != 'average':
             raise UserError(f"Recalculation aborted: Product {product.display_name} is configured as '{product.cost_method}' (Expected 'average').")
        
        # SAFETY: Subtract 1 second from start_date to avoid DB precision issues.
        start_date = start_date - datetime.timedelta(seconds=1)
        
        _logger.info(f"DEBUG: Starting Recalc for {product.display_name} from {start_date}")
        _logger.info(f"DEBUG: Initial Balance: Qty={initial_qty}, Value={initial_value}")

        # 1. Initialize Running Balance
        running_qty = initial_qty
        running_value = initial_value
        
        # 2. Fetch Future Moves (The Splash Zone)
        future_moves = self.search([
            ('product_id', '=', product.id),
            ('date', '>=', start_date),
            ('state', '=', 'done')
        ], order='date asc, id asc')
        
        _logger.info(f"DEBUG: Found {len(future_moves)} moves to process.")
        for m in future_moves:
             _logger.info(f"DEBUG: Move ID {m.id} | Date {m.date} | In: {m.is_in} Out: {m.is_out} | Qty: {m.quantity} | Val: {m.value}")

        # --- SNAPSHOT & UPDATE PHASE ---

        # --- SNAPSHOT & UPDATE PHASE ---
        # --- COST UPDATE & CLEANUP PHASE ---
        
        # A. Cleanup Phase: ALWAYS Remove 'Values' that contradict our new history.
        future_pvals = self.env['product.value'].sudo().search([
             ('product_id', '=', product.id),
             ('date', '>=', start_date)
        ])
        if future_pvals:
             future_pvals.unlink()

        # B. Safe Update (Optional): Update Standard Price if requested
        # Only if strict value provided (> 0 to avoid accidental zeroing)
        if new_standard_price:
             self._set_standard_price_safe(product, new_standard_price)


        moves_affected = 0
        total_value_change = 0.0
        
        for move in future_moves:
            # Skip non-valued moves (e.g. internal transfers without value)
            if not move.is_in and not move.is_out:
                continue

            current_val = move.value
            new_val = current_val # Default to no change
            
            # --- INCOMING MOVES (TRUSTED INPUT) ---
            if move.is_in:
                val_to_add = move.value 
                
 
                
                # SPECIAL LOGIC: Sales Returns (Customer returns goods)
                # If this move is a return of a previous move, we must use the COST of that previous move.
                # Since we might have just recalculated that previous move in this very loop, 
                # we read the origin's current state to get the correct "Restoration Price".
                if move.origin_returned_move_id:
                    origin = move.origin_returned_move_id
                    # Calculate Unit Cost of the original move (e.g. the Delivery)
                    # We use safe division just in case
                    origin_qty = origin.quantity
                    if not float_is_zero(origin_qty, precision_rounding=product.uom_id.rounding):
                        # The origin value might have been updated by this script just seconds ago!
                        restored_unit_cost = origin.value / origin.quantity
                        
                        # Recalculate THIS return's total value based on that cost
                        new_return_val = move.quantity * restored_unit_cost
                        
                        # If the Return's recorded value differs from the Origin's unit cost -> FIX IT
                        if abs(val_to_add - new_return_val) > 0.01:
                            move.write({
                                'value': new_return_val,
                                'price_unit': restored_unit_cost
                            })
                            val_to_add = new_return_val
                            # We count this as an affected move too
                            moves_affected += 1
                            total_value_change += abs(move.value - new_return_val)

                # Add to the snowball
                running_qty += move.quantity
                running_value += val_to_add
                _logger.info(f"DEBUG: [IN] Move {move.id}. Value added: {val_to_add}. New Balance: Qty={running_qty}, Val={running_value}")

            # --- OUTGOING MOVES (DERIVED OUTPUT) ---
            elif move.is_out:
                # Calculate Cost based on Running Average BEFORE this move
                # AVCO = Total Value / Total Qty
                
                if float_is_zero(running_qty, precision_rounding=product.uom_id.rounding) or running_qty <= 0:
                    # Fallback: Zero or Negative Stock. 
                    # Use Standard Price (Cost stored on product) as best guess
                    unit_cost = product.standard_price
                else:
                    unit_cost = running_value / running_qty

                # Recalculate this move's total value
                new_val = move.quantity * unit_cost
                
                # Update Record if there is a discrepancy
                # We check difference > 0.01 currency unit
                if abs(current_val - new_val) > 0.01:
                    # Write to DB - OPERATIONAL UPDATE ONLY
                    move.write({
                        'value': new_val,
                        'price_unit': unit_cost
                    })
                    moves_affected += 1
                    total_value_change += abs(current_val - new_val)
                
                # Update Running Balance (Subtract exit)
                running_qty -= move.quantity
                running_value -= new_val
                _logger.info(f"DEBUG: [OUT] Move {move.id}. Cost applied: {unit_cost}. New Balance: Qty={running_qty}, Val={running_value}")

        # 3. Finalize: Update Product Cost
        # Theoretically, the final running_value/running_qty is the new Standard Price
        new_standard_price = product.standard_price
        if running_qty > 0:
            new_standard_price = running_value / running_qty
            # USE SAFE UPDATE to avoid nuking history
            self._set_standard_price_safe(product, new_standard_price)

        return {
            'moves_count': moves_affected,
            'total_correction': total_value_change,
            'final_qty': running_qty,
            'final_value': running_value,
            'final_cost': new_standard_price
        }

    def _set_standard_price_safe(self, product, new_price):
        """
        Updates standard_price via Raw SQL to bypass Odoo 19's:
        1. Aggressive automatic revaluation (ORM write trigger).
        2. 'ir.property' deprecation/issues (KeyError).
        
        Handles both JSONB (Company-Dependent) and Float (Global) storage correctly.
        """
        import json
        
        # Determine strict storage type from model definition
        # Use _fields to check if company_dependent (JSONB)
        field_def = product._fields.get('standard_price')
        is_jsonb = field_def.company_dependent if field_def else False
        
        query_read = "SELECT standard_price FROM product_product WHERE id = %s"
        self.env.cr.execute(query_read, (product.id,))
        result = self.env.cr.fetchone()
        
        if not result:
            return # Product not found?
            
        raw_val = result[0]
        company_id = str(self.env.company.id)
        
        # 1. Handle JSONB Storage (Modern Odoo Company-Dependent)
        if is_jsonb:
             current_json = {}
             
             # Parse existing value if any
             if isinstance(raw_val, dict):
                 current_json = raw_val
             elif isinstance(raw_val, str):
                 try:
                     current_json = json.loads(raw_val)
                 except:
                     current_json = {} 
             # If None, current_json remains {}
                 
             # Update for current company
             current_json[company_id] = new_price
             
             # Write back as JSON String
             query_update = "UPDATE product_product SET standard_price = %s WHERE id = %s"
             self.env.cr.execute(query_update, (json.dumps(current_json), product.id))
             _logger.info(f"SAFE SQL UPDATE (JSONB): Updated standard_price for {product.display_name} to {new_price}")

        # 2. Handle Simple Float Storage (Legacy or specific config)
        else:
             query_update = "UPDATE product_product SET standard_price = %s WHERE id = %s"
             self.env.cr.execute(query_update, (new_price, product.id))
             _logger.info(f"SAFE SQL UPDATE (FLOAT): Updated standard_price for {product.display_name} to {new_price}")
             
        # Invalidating cache is crucial so Odoo sees the new value next time it reads
        product.invalidate_recordset(['standard_price'])

    @api.model
    def _get_historical_balance_at_date(self, product_id, cutoff_date):
        """
        Fast SQL 'Genesis' calculation.
        Returns (qty, value) accumulated strictly BEFORE cutoff_date.
        """
        query = """
            SELECT 
                SUM(CASE WHEN is_in THEN quantity ELSE -quantity END) as total_qty,
                SUM(CASE WHEN is_in THEN value ELSE -value END) as total_value
            FROM 
                stock_move 
            WHERE 
                product_id = %s 
                AND state = 'done' 
                AND date < %s
                AND (is_in = TRUE OR is_out = TRUE)
        """
        self.env.cr.execute(query, (product_id, cutoff_date))
        res = self.env.cr.dictfetchone()
        return (res.get('total_qty') or 0.0), (res.get('total_value') or 0.0)
