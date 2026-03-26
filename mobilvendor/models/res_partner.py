from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Add the new field 'mobilvendor_id'
    mobilvendor_id = fields.Char(string='Mobilvendor ID', index=True)
    address_mobilvendor_id = fields.Char(string='Mobilvendor Address ID', index=True)

    # Visit Schedule (Source of Truth)
    route_line_ids = fields.Many2many(
        'mobilvendor.route.line',
        compute='_compute_route_line_ids',
        search='_search_route_line_ids',
        string='Visit Schedule',
        help="Shows visits assigned to this contact OR any of its addresses/branches."
    )

    # Associated Routes (Computed: A client can be in N routes)
    mobilvendor_route_ids = fields.Many2many(
        'mobilvendor.route',
        string='Assigned Routes (MV)',
        compute='_compute_mobilvendor_route_ids',
        store=True,
        help="Routes where this client has scheduled visits."
    )

    @api.depends('mobilvendor_route_ids', 'child_ids')
    def _compute_route_line_ids(self):
        for partner in self:
            # Step A: Collect all relevant IDs: Myself + My children (Branches)
            # If I am a branch, 'child_ids' will be empty and I will only search for myself.
            all_partner_ids = [partner.id] + partner.child_ids.ids

            # Step B: Search for all route lines pointing to any of those IDs
            lines = self.env['mobilvendor.route.line'].search([
                ('partner_address_id', 'in', all_partner_ids)
            ])

            # Step C: Assign for visualization
            partner.route_line_ids = lines

    @api.depends('route_line_ids.route_id', 'child_ids.route_line_ids.route_id')
    def _compute_mobilvendor_route_ids(self):
        for partner in self:
            # 1. Routes assigned directly to this contact (e.g., a standalone address)
            direct_routes = partner.route_line_ids.mapped('route_id')

            # 2. Routes assigned to its children/branches (if it is a parent company)
            child_routes = partner.child_ids.route_line_ids.mapped('route_id')

            # 3. Merge both sets (The | operator automatically removes duplicates)
            partner.mobilvendor_route_ids = direct_routes | child_routes

    def _search_route_line_ids(self, operator, value):
        lines = self.env['mobilvendor.route.line'].search([('id', operator, value)])

        partner_ids = lines.mapped('partner_address_id').ids

        return [('|'), ('id', 'in', partner_ids), ('child_ids', 'in', partner_ids)]