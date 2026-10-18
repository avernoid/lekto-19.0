from odoo import api, fields, models

# Technical meaning of a state, shared by carrier integrations and the driver portal.
DELIVERY_STATE_CODES = [
    ('pending', 'Pending'),
    ('recorded', 'Recorded by the carrier'),
    ('in_transit', 'In transit'),
    ('delivered', 'Delivered'),
    ('incident', 'Incident'),
    ('canceled', 'Cancelled'),
]
# Codes after which nothing is asked to the carrier any more.
FINAL_CODES = ('delivered', 'canceled')


class StockDeliveryState(models.Model):
    _name = 'stock.delivery.state'
    _description = 'Delivery State'
    _order = 'sequence, id'
    _check_company_auto = True

    name = fields.Char(required=True, translate=True, help='Name of the state as users and customers see it.')
    sequence = fields.Integer(default=10, help='Order of the states in lists and in the state selector.')
    active = fields.Boolean(default=True, help='Archive the state to hide it without deleting it.')
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company,
        help='Company this state belongs to.')
    code = fields.Selection(
        DELIVERY_STATE_CODES, string='Technical Code', index=True,
        help='What the state means. Carrier integrations use it to set the state, whatever its name.')
    icon = fields.Char(string='Font Awesome Icon', help='Icon class, e.g. fa-truck.')
    is_result_state = fields.Boolean(
        string='Is Result State',
        help='Final outcome of the delivery: the delivery date is stored when a transfer reaches it.')
    result_type = fields.Selection(
        [('success', 'Success'), ('partial', 'Partial Success'), ('failure', 'Failure')],
        help='How the delivery ended when it reaches this final state.')
    mail_template_id = fields.Many2one(
        'mail.template', string='Email Template', domain=[('model', '=', 'stock.picking')],
        help='Email sent to the transfer contact when the transfer enters this state.')

    @api.onchange('is_result_state')
    def _onchange_is_result_state(self):
        if not self.is_result_state:
            self.result_type = False

    @api.model
    def _get_by_code(self, code, company):
        """State of the company for a technical code (the first one by sequence).

        The default states are created for the company that installs the module: another
        company gets its own copy the first time it needs one."""
        if not code:
            return self.browse()
        state = self.search([('code', '=', code), ('company_id', 'in', company.ids)], limit=1)
        if not state:
            template = self.sudo().with_context(active_test=False).search([('code', '=', code)], limit=1)
            if template:
                state = template.copy({'company_id': company.id, 'name': template.name, 'active': True})
        return state.with_env(self.env)
