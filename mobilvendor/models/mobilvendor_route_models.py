# -*- coding: utf-8 -*-
from odoo import models, fields, api

# =========================================================
# 0. NEW INTERMEDIATE MODEL (Employee-Route Relationship)
# =========================================================

class MobilvendorRouteEmployee(models.Model):
    _name = 'mobilvendor.route.employee'
    _description = 'Route Assignment'
    _rec_name = 'route_id'

    # Relationship with the Employee
    employee_id = fields.Many2one('hr.employee', string='Seller', required=True, ondelete='cascade')

    # Relationship with the Route
    route_id = fields.Many2one('mobilvendor.route', string='Route', required=True, ondelete='cascade')

    # REQUESTED FIELD: Relationship status
    active = fields.Boolean(string='Active Assignment', default=True)

    _sql_constraints = [
        ('employee_route_unique', 'unique(employee_id, route_id)', 'A seller can be assigned to a route only once.')
    ]

# =========================================================
# 1. SUPPORT TABLES (User Configurable Dropdowns)
# =========================================================

class MobilvendorRouteOperationType(models.Model):
    _name = 'mobilvendor.route.operation.type'
    _description = 'Mobilvendor Operation Type'

    name = fields.Char(string='Name', required=True)
    _sql_constraints = [('name_uniq', 'unique (name)', 'The operation type name must be unique.')]


class MobilvendorRouteSegment(models.Model):
    _name = 'mobilvendor.route.segment'
    _description = 'Mobilvendor Route Segment'

    name = fields.Char(string='Name', required=True)
    _sql_constraints = [('name_uniq', 'unique (name)', 'The segment name must be unique.')]


class MobilvendorRouteTerritory(models.Model):
    _name = 'mobilvendor.route.territory'
    _description = 'Mobilvendor Route Territory'

    name = fields.Char(string='Name', required=True)
    _sql_constraints = [('name_uniq', 'unique (name)', 'The territory name must be unique.')]


class MobilvendorRouteAgency(models.Model):
    _name = 'mobilvendor.route.agency'
    _description = 'Mobilvendor Agency'

    name = fields.Char(string='Name', required=True)
    _sql_constraints = [('name_uniq', 'unique (name)', 'The agency name must be unique.')]


# =========================================================
# 2. MAIN MODEL: THE ROUTE (Header)
# =========================================================

class MobilvendorRoute(models.Model):
    _name = 'mobilvendor.route'
    _description = 'Mobilvendor Sales Route'
    _rec_name = 'name'

    # --- Identification ---
    name = fields.Char(string='Route Name', required=True)
    shortname = fields.Char(string='Short Name / Internal Code', index=True)
    pcg_code = fields.Char(string='PCG Code', size=3, help="Legacy code from the previous system")

    # --- Mobilvendor Synchronization (Keys) ---
    mobilvendor_id = fields.Char(string='MV Route Code', required=True, copy=False, index=True,
                                 help="Main synchronization key")

    # Physical Location (Warehouse)
    storage_location_id = fields.Many2one(
        'stock.location',
        string='Resupply Warehouse (MV)',
        domain="[('usage', '=', 'internal')]",
        help="Physical Odoo location where goods are deducted for this route."
    )

    # --- Classification ---
    operation_type_id = fields.Many2one('mobilvendor.route.operation.type', string='Operation Type')
    segment_id = fields.Many2one('mobilvendor.route.segment', string='Functional Segment')
    territory_id = fields.Many2one('mobilvendor.route.territory', string='Territory')
    agency_id = fields.Many2one('mobilvendor.route.agency', string='Agency')

    # --- Accounting Journals ---
    invoice_journal_id = fields.Many2one(
        'account.journal',
        string='Invoice Journal',
        domain="[('type', '=', 'sale')]"
    )
    payment_journal_id = fields.Many2one(
        'account.journal',
        string='Payment Journal',
        domain="[('type', 'in', ('bank', 'cash'))]"
    )

    # --- System ---
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    # --- Inverse Relations ---
    line_ids = fields.One2many('mobilvendor.route.line', 'route_id', string='Visit Itinerary')
    employee_assignment_ids = fields.One2many(
        'mobilvendor.route.employee',
        'route_id',
        string='Assigned Sellers'
    )

    partner_count = fields.Integer(compute='_compute_partner_count', string='Customer Count')

    _sql_constraints = [
        ('mobilvendor_id_uniq', 'unique (mobilvendor_id)',
         'The Mobilvendor Route Code (mobilvendor_id) must be unique.')
    ]

    def _compute_partner_count(self):
        for route in self:
            # Contamos cuántas direcciones únicas hay en las líneas
            unique_partners = route.line_ids.mapped('partner_address_id')
            route.partner_count = len(unique_partners)

    def action_view_customers(self):
        """
        Opens a list view showing unique partners associated with this route.
        Updated to use a specific view with the Parent Customer column.
        """
        self.ensure_one()
        # Get unique partner IDs from the itinerary lines
        unique_partner_ids = self.line_ids.mapped('partner_address_id').ids

        return {
            'name': 'Customers in Route',
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            # Force the specific view we created
            'views': [(self.env.ref('mobilvendor.view_partner_list_mobilvendor_route').id, 'list'), (False, 'form')],
            'view_mode': 'list,form',
            'domain': [('id', 'in', unique_partner_ids)],
            'context': {'create': False}
        }

# =========================================================
# 3. DETAILED MODEL: ITINERARY (Route Details)
# =========================================================

class MobilvendorRouteLine(models.Model):
    _name = 'mobilvendor.route.line'
    _description = 'Route Visit Detail'
    _order = 'week, day, sequence'

    route_id = fields.Many2one('mobilvendor.route', string='Route', required=True, ondelete='cascade')

    # Specific Address/Branch Relationship
    # No domain restriction applied, allowing any partner record (company or individual)
    partner_address_id = fields.Many2one(
        'res.partner',
        string='Branch/Address',
        required=True
    )

    partner_address_txt = fields.Char(
        string='Full Address',
        related='partner_address_id.contact_address',
        readonly=True
    )

    day = fields.Selection([
        ('1', 'Sunday'), ('2', 'Monday'), ('3', 'Tuesday'),
        ('4', 'Wednesday'), ('5', 'Thursday'), ('6', 'Friday'), ('7', 'Saturday')
    ], string='Day')

    sequence = fields.Integer(string='Sequence')
    week = fields.Integer(string='Week')

    # External ID (Standardized)
    mobilvendor_id = fields.Char(string='API Detail ID', copy=False, index=True)

    active = fields.Boolean(string='Active', default=True)