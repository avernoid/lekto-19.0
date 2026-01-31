from odoo import models, fields

class CrmTeam(models.Model):
    _inherit = 'crm.team'

    portal_contact_visibility = fields.Selection([
        ('assigned', 'View Assigned Contacts'),
        ('assigned_and_unassigned', 'View Assigned & Unassigned')
    ], string='Portal Visibility', help="""Defines the visibility of contacts in the Partner Portal for members of this team:
- View Assigned Contacts: Members see only contacts where they are the Salesperson.
- View Assigned & Unassigned: Members see their assigned contacts AND contacts with no Salesperson assigned.
Note: This rule is additive with User Group permissions.""")
