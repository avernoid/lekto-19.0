from odoo import api, models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    journal_assign_to_ids = fields.Many2many(
        comodel_name='res.users',
        string='Journal - Assigned to',
        compute='_compute_journal_assign_to_ids',
        store=True,
        help="Technical field used to store the users assigned to the journal of this move. Used for record rules."
    )

    @api.depends('journal_id', 'journal_id.assign_to_ids', 'journal_id.journal_group_ids')
    def _compute_journal_assign_to_ids(self):
        """
        Compute the related users who have access to the journal of the account move.

        This method is a computed field that retrieves the related users from the journal's
        'assign_to_ids' field. It uses the 'env.cr.execute' method to perform a SQL query
        to fetch the journal_id of the current account move record. Then, it fetches the
        corresponding journal record and retrieves the 'assign_to_ids' field.
        This is to avoid the error maximum recursion depth exceeded in comparison when trying to get the journal_id from account.move (a computed field).

        Parameters:
        self (account.move): The current record of the account move model.

        Returns:
        None: The method updates the 'journal_assign_to_ids' field of the current record.
        """
        for record in self:
            journal = record.journal_id._origin if record.journal_id else record.journal_id
            record.journal_assign_to_ids = journal.assign_to_ids.ids if journal else []
            record.journal_group_ids = journal.journal_group_ids.ids if journal else []

    journal_group_ids = fields.Many2many(
        comodel_name='res.groups',
        string='Journal - Allowed Groups',
        compute='_compute_journal_assign_to_ids',
        store=True,
        help="Technical field used to store the groups allowed on the journal of this move."
    )
