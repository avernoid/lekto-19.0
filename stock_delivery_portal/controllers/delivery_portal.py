from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
import base64

class DeliveryPortal(CustomerPortal):

    def _get_delivery_domain(self):
        partner = request.env.user.partner_id
        return [
            ('delivery_partner_id', '=', partner.id),
            ('state', 'not in', ['draft', 'cancel']),
            ('picking_type_code', '=', 'outgoing'),
            ('hide_from_portal', '=', False)
        ]

    @http.route(['/my/delivery', '/my/delivery/page/<int:page>'], type='http', auth="user", website=True)
    def delivery_list(self, page=1, sortby='date', search=False, filter_state=False, filter_type=False, history=False, **kw):
        Picking = request.env['stock.picking'].sudo()
        domain = self._get_delivery_domain()
        
        # Determine if we are in history mode
        history_mode = bool(history and history != '0')

        if history_mode:
            # Only show finalized states
            domain += [('delivery_state_id.is_result_state', '=', True)]
        else:
            # Default: Hide finalized states (Show active states OR no state)
            domain += ['|', ('delivery_state_id', '=', False), ('delivery_state_id.is_result_state', '=', False)]

        # 0. Get attributes for smart filters (based on all assigned pickings)
        # We search all to get unique values for filters
        # Note: We probably want filters to respect the history/active mode context
        # But for now, let's keep them broad or restrict them?
        # Let's restrict available filters to the current scope (history vs active) to avoid confusion
        all_pickings_in_scope = Picking.search(domain)
        available_states = all_pickings_in_scope.mapped('delivery_state_id').sorted('sequence')
        available_types = all_pickings_in_scope.mapped('picking_type_id').sorted('name')

        # 1. Search logic (if search term provided)
        if search:
            search_terms = [
                ('name', 'ilike', search),
                ('origin', 'ilike', search),
                ('partner_id.name', 'ilike', search),
                ('move_line_ids.product_id.name', 'ilike', search),
                ('move_line_ids.product_id.default_code', 'ilike', search),
                ('move_line_ids.product_id.barcode', 'ilike', search),
                ('move_line_ids.result_package_id.name', 'ilike', search),
            ]
            if len(search_terms) == 1:
                domain += search_terms
            else:
                # Construir lista OR plana: n condiciones requieren n-1 '|' al inicio
                or_domain = ['|'] * (len(search_terms) - 1)
                for term in search_terms:
                    or_domain.append(term)
                domain += or_domain
        
        # 2. Apply Filters
        if filter_state:
            domain += [('delivery_state_id', '=', int(filter_state))]
        if filter_type:
            domain += [('picking_type_id', '=', int(filter_type))]

        # Count and Pager
        total = Picking.search_count(domain)
        
        url_args = {'sortby': sortby, 'search': search, 'filter_state': filter_state, 'filter_type': filter_type}
        if history_mode:
            url_args['history'] = 1
            
        pager = request.website.pager(
            url='/my/delivery',
            total=total,
            page=page,
            step=20,
            url_args=url_args
        )
        
        pickings = Picking.search(domain, limit=20, offset=pager['offset'], order='scheduled_date asc')
        
        values = {
            'pickings': pickings,
            'pager': pager,
            'search': search,
            'sortby': sortby,
            'default_url': '/my/delivery',
            'available_states': available_states,
            'available_types': available_types,
            'filter_state': int(filter_state) if filter_state else False,
            'filter_type': int(filter_type) if filter_type else False,
            'history': history_mode,
        }
        return request.render("stock_delivery_portal.delivery_app_home", values)

    @http.route(['/my/delivery/<int:picking_id>'], type='http', auth="user", website=True)
    def delivery_detail(self, picking_id, **kw):
        try:
            picking = request.env['stock.picking'].sudo().browse(picking_id)
            # Security Check
            if not picking.exists() or picking.delivery_partner_id != request.env.user.partner_id:
                return request.redirect('/my/delivery')
            
            # Pass non-final states for the action buttons
            non_final_states = request.env['stock.delivery.state'].sudo().search([('is_result_state', '=', False)])
            
            evidence_photos = request.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'stock.picking'),
                ('res_id', '=', picking.id),
                ('mimetype', 'like', 'image/')
            ])
            
            # Using native/extra fields (total_packages/total_bundles) in template
            
            response = request.render("stock_delivery_portal.delivery_app_detail", {
                'picking': picking,
                'evidence_photos': evidence_photos,
                'non_final_states': non_final_states,
            })
            # Force rendering to catch template errors inside this try block
            response.flatten()
            return response
        except Exception as e:
            return request.make_response(f"DEBUG ERROR: {str(e)}")
    
    @http.route(['/my/delivery/search'], type='jsonrpc', auth="user")
    def search_delivery(self, query):
        if not query:
            return {'match_type': 'none'}

        domain = self._get_delivery_domain()
        Picking = request.env['stock.picking'].sudo()

        # 1. Buscar por código de barras exacto de picking (si existiera ese campo)
        # (No estándar en stock.picking, omitir si no se usa)

        # 2. Buscar por código de barras exacto de producto
        pickings = Picking.search(domain + [('move_line_ids.product_id.barcode', '=', query)])
        if pickings:
            if len(pickings) == 1:
                return {'match_type': 'exact', 'action_url': f'/my/delivery/{pickings.id}'}
            else:
                return {'match_type': 'multiple', 'picking_ids': pickings.ids}

        # 3. Buscar por referencia interna exacta de producto
        pickings = Picking.search(domain + [('move_line_ids.product_id.default_code', '=', query)])
        if pickings:
            if len(pickings) == 1:
                return {'match_type': 'exact', 'action_url': f'/my/delivery/{pickings.id}'}
            else:
                return {'match_type': 'multiple', 'picking_ids': pickings.ids}

        # 4. Buscar por nombre de picking, origen, nombre de producto, nombre de paquete, barcode parcial
        try:
            or_domain = ['|'] * 5 + [
                ('name', 'ilike', query),
                ('origin', 'ilike', query),
                ('move_line_ids.product_id.name', 'ilike', query),
                ('move_line_ids.product_id.barcode', 'ilike', query),
                ('move_line_ids.product_id.default_code', 'ilike', query),
                ('move_line_ids.result_package_id.name', 'ilike', query),
            ]
            pickings = Picking.search(domain + or_domain)
            if not pickings:
                return {'match_type': 'none'}
            if len(pickings) == 1:
                return {'match_type': 'exact', 'action_url': f'/my/delivery/{pickings.id}'}
            return {'match_type': 'multiple', 'picking_ids': pickings.ids}
        except Exception as e:
            return {'match_type': 'error', 'message': str(e)}

    @http.route(['/my/delivery/<int:picking_id>/finalize'], type='http', auth="user", website=True)
    def delivery_finalize_view(self, picking_id, **kw):
        picking = request.env['stock.picking'].sudo().browse(picking_id)
        if not picking.exists() or picking.delivery_partner_id != request.env.user.partner_id:
            return request.redirect('/my/delivery')
        
        # Get allowed final states (where is_result_state=True)
        final_states = request.env['stock.delivery.state'].sudo().search([('is_result_state', '=', True)])

        return request.render("stock_delivery_portal.delivery_app_finalize", {
            'picking': picking,
            'final_states': final_states,
        })

    @http.route(['/my/delivery/<int:picking_id>/submit'], type='http', auth="user", website=True, methods=['POST'])
    def delivery_submit(self, picking_id, **kw):
        picking = request.env['stock.picking'].sudo().browse(picking_id)
        if not picking.exists() or picking.delivery_partner_id != request.env.user.partner_id:
             return request.redirect('/my/delivery')

        delivery_state_id = int(kw.get('delivery_state_id'))
        receiver_name = kw.get('receiver_name')
        delivery_notes = kw.get('delivery_notes')
        signature = kw.get('signature') # Base64 string from canvas
        photo = kw.get('photo') # File upload
        photo_64 = kw.get('photo_64') # Base64 string from JS compression
        
        vals = {
            'delivery_state_id': delivery_state_id,
        }
        if receiver_name:
            vals['delivery_receiver_name'] = receiver_name
        if delivery_notes:
            vals['delivery_notes'] = delivery_notes
        if signature:
            if ',' in signature:
                signature = signature.split(',')[1]
            vals['signature'] = signature

        picking.write(vals)

        # Handle Photo (Prioritize Optimized Base64)
        photo_data = False
        if photo_64:
            if ',' in photo_64:
                photo_data = base64.b64decode(photo_64.split(',')[1])
            else:
                photo_data = base64.b64decode(photo_64)
        elif photo:
            photo_data = photo.read()

        if photo_data:
            state_name = picking.delivery_state_id.name
            picking.message_post(
                body=f"Evidencia Estado de Entrega: {state_name}",
                message_type='comment',
                subtype_xmlid='mail.mt_note',
                attachments=[(f'Delivery_Photo_{picking.name}.webp', photo_data)]
            )

        return request.redirect('/my/delivery?success=Delivery Finalized')

    @http.route(['/my/delivery/<int:picking_id>/upload_photo'], type='http', auth="user", website=True, methods=['POST'])
    def delivery_upload_photo(self, picking_id, **kw):
        picking = request.env['stock.picking'].sudo().browse(picking_id)
        if not picking.exists() or picking.delivery_partner_id != request.env.user.partner_id:
            return request.redirect('/my/delivery')
        
        photo = kw.get('photo')
        photo_64 = kw.get('photo_64')
        
        photo_data = False
        if photo_64:
            if ',' in photo_64:
                photo_data = base64.b64decode(photo_64.split(',')[1])
            else:
                photo_data = base64.b64decode(photo_64)
        elif photo:
            photo_data = photo.read()

        if photo_data:
            state_name = picking.delivery_state_id.name or 'Unknown State'
            picking.message_post(
                body=f"Evidencia Estado de Entrega: {state_name}",
                message_type='comment',
                subtype_xmlid='mail.mt_note',
                attachments=[(f'Delivery_Photo_{picking.name}.webp', photo_data)]
            )
        
        # Redirect back to detail view
        return request.redirect(f'/my/delivery/{picking.id}')

    # PWA Support Routes - DELEGATED TO PORTAL_APP_LAUNCHER
    # We use /portal_app/manifest.webmanifest?app_mode=delivery
    # We use /service-worker.js (served by launcher)

    @http.route(['/my/delivery/update_state'], type='jsonrpc', auth="user")
    def update_delivery_state(self, picking_id, state_id):
        picking = request.env['stock.picking'].sudo().browse(picking_id)
        if not picking.exists() or picking.delivery_partner_id != request.env.user.partner_id:
            return {'error': 'Access Denied'}
        
        picking.write({'delivery_state_id': state_id})
        return {'success': True}
