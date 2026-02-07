from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    origin_move_id = fields.Many2one(
        comodel_name='account.move',
        string='Rectified Document',
        domain="[('id', '!=', id)]",
        help='Reference to the original document that is being rectified.'
    )
    origin_number = fields.Char(string='Rectified Document Reference', help='Number or reference of the original document.')
    origin_l10n_latam_document_type_id = fields.Many2one(
        comodel_name='l10n_latam.document.type',
        string='Rectified Document Type',
        help='Type of the original document.'
    )
    origin_invoice_date = fields.Date(string='Rectified Date', help='Date of the original document.')

    internal_type = fields.Selection(
        related="l10n_latam_document_type_id.internal_type",
        store=False
    )


    @api.onchange('origin_move_id', 'reversed_entry_id', 'debit_origin_id')
    def _onchange_origin_move_id(self):
        self._compute_origin_document_data()

    def _compute_origin_document_data(self):
        for move in self:
            origin_move_id = move.origin_move_id or move.reversed_entry_id or move.debit_origin_id
            document_type, invoice_date, number = self.get_data_from_origin_move_id(origin_move_id)
            move.update({
                'origin_l10n_latam_document_type_id': document_type,
                'origin_number': number,
                'origin_invoice_date': invoice_date
            })

    @staticmethod
    def get_data_from_origin_move_id(origin_move_id):
        document_type = False
        invoice_date = False
        number = False
        if origin_move_id and origin_move_id.l10n_latam_document_type_id:
            number = origin_move_id.name.replace(' ', '') if origin_move_id.name else ''
            document_type = origin_move_id.l10n_latam_document_type_id.id
            invoice_date = origin_move_id.invoice_date
        return document_type, invoice_date, number

    def _reverse_moves(self, default_values_list=None, cancel=False):
        list_moves = super()._reverse_moves(default_values_list=default_values_list, cancel=cancel)
        for obj_move in list_moves:
            obj_move._compute_origin_document_data()
        return list_moves

    @api.model
    def create(self, vals):
        move = super().create(vals)
        move._compute_origin_document_data()
        return move
