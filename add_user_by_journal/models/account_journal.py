from odoo import models, fields, api, _


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    assign_to_ids = fields.Many2many(
        comodel_name='res.users',
        string='Assigned in Dashboard',
        check_company=False,
        help="Users assigned to this journal. Restricted users will only see journals where they are assigned."
    )
    journal_group_ids = fields.Many2many(
        comodel_name='res.groups',
        string='Allowed Groups',
        check_company=False,
        help="User groups that have access to this journal. Users belonging to these groups will see this journal."
    )
    access_instruction = fields.Html(
        string='Access Policy',
        compute='_compute_access_instruction',
        help="Dynamic explanation of who can access this journal."
    )
    can_edit_journal_security = fields.Boolean(
        compute='_compute_can_edit_journal_security',
        string='Can Edit Security'
    )

    @api.depends_context('uid')
    def _compute_can_edit_journal_security(self):
        for journal in self:
            journal.can_edit_journal_security = self.env.user.has_group('add_user_by_journal.res_groups_admin_journal_access')

    @api.depends('assign_to_ids', 'journal_group_ids')
    def _compute_access_instruction(self):
        for journal in self:
            if not journal.assign_to_ids and not journal.journal_group_ids:
                # Case 1: Public (Both Empty)
                instruction = _("""
                    <div class="alert alert-info" role="alert">
                        <strong>✅ Public Access:</strong> This journal is visible to <b>ALL users</b> with accounting rights.<br/>
                        <small>(Because both 'Assigned Users' and 'Allowed Groups' are empty)</small>
                    </div>
                """)
            else:
                # Case 2: Restricted (At least one set)
                users_list = ", ".join(journal.assign_to_ids.mapped('name')) or _("<i>None</i>")
                groups_list = ", ".join(journal.journal_group_ids.mapped('name')) or _("<i>None</i>")
                
                instruction = _("""
                    <div class="alert alert-warning" role="alert">
                        <strong>🔒 Restricted Access:</strong> Only the following will have access:
                        <ul>
                            <li><b>Users:</b> %s</li>
                            <li><b>Groups:</b> %s</li>
                            <li><b>Administrators</b> (Always have access)</li>
                        </ul>
                    </div>
                """) % (users_list, groups_list)
            journal.access_instruction = instruction
