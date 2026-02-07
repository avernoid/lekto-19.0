from odoo import api, fields, models, _
import pytz
from odoo.exceptions import RedirectWarning, UserError, ValidationError

class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'view.multicompany.country.filter.mixin']

    ple_state = fields.Selection(
        selection=[
            ('0', '0'),
            ('1', '1'),
            ('2', '2'),
            ('6', '6'),
            ('7', '7'),
            ('8', '8'),
            ('9', '9')],
        string='Status PLE',
        help='Indicates the status of the document in the PLE. '
             '1: Registered in the period. '
             '2: Cancelled document. '
             '8: Registered in a previous period. '
             '9: Correction of a previous period.'
    )
    ple_its_declared = fields.Boolean(
        string='Declared?',
        help='Checked if this document has already been declared to SUNAT.'
    )
    ple_date = fields.Date(
        string='Date PLE',
        help='Date used to determine the PLE reporting period. Defaults to Invoice Date.'
    )

    bool_pay_invoice = fields.Boolean(
        string='Paid Invoice Indicator',
        help='Indicates if the payment voucher has been cancelled (paid).'
    )

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type in ('form'):
            tags = [('group', 'ple_group'), ('field', 'bool_pay_invoice')]
            arch, view = self._tags_invisible_per_country(arch, view, view_type, tags, [self.env.ref('base.pe')])
        return arch, view

    def update_ple_state(self):
        recs = self.filtered(lambda x: x.move_type in ['out_invoice', 'out_refund'])
        recs.update({'ple_state': '1'})

    @api.onchange('date')
    def onchange_ple_date_from_date(self):
        self.ple_date = self.date

    @api.onchange('invoice_date')
    def onchange_ple_date_from_invoice_date(self):
        self.ple_date = self.invoice_date

    @api.model
    def _convert_date_timezone(self, date_order, format_time='%Y-%m-%d %H:%M:%S'):
        user_tz = pytz.timezone(self.env.user.tz) if self.env.user.tz else pytz.utc
        date_tz = pytz.utc.localize(date_order).astimezone(user_tz)
        date_order = date_tz.strftime(format_time)
        return date_order

    @api.model_create_multi
    def create(self, values):
        for vals in values:
            if vals.get('date'):
                vals['ple_date'] = vals['date']
            elif vals.get('invoice_date'):
                vals['ple_date'] = vals['invoice_date']
            else:
                vals['ple_date'] = fields.Date.context_today(self)
        obj = super(AccountMove, self).create(values)
        obj.update_ple_state()
        obj.update_lines_correlative()
        return obj

    def write(self, values):
        for rec in self:
            rec.update_cancel_ple_state(values)
            prefix = rec.get_ple_type_contributor()
            i = 1
            for line in rec.line_ids:
                line.update_correlative_cr(prefix, i)
                i += 1
            rec.change_ple_state_version(values)
        return super(AccountMove, self).write(values)

    def update_lines_correlative(self):
        for obj in self:
            prefix = obj.get_ple_type_contributor()
            obj.line_ids.update_correlative(prefix)

    def update_cancel_ple_state(self, values):
        self.ensure_one()
        document_type_id = self.l10n_latam_document_type_id and self.l10n_latam_document_type_id.code in ['01', '03']
        if self.move_type in ['out_invoice', 'out_refund'] and document_type_id and values.get('state') and values['state'] == 'cancel':
            values['ple_state'] = '2'
        return values

    def get_ple_type_contributor(self):
        self.ensure_one()
        new_name = self.journal_id.ple_journal_correlative or ''
        return new_name

    def change_ple_state_version(self, values):
        if self.move_type in ['out_invoice', 'out_refund']:
            if 'ple_date' in values:
                ple_month = values['ple_date'].split('-')
                for recs in self:
                    if recs.invoice_date and recs.date:
                        if recs.invoice_date.month < int(ple_month[1]) or recs.invoice_date.year < int(ple_month[0]):
                            values['ple_state'] = '8'
                        else:
                            values['ple_state'] = '1'
        self.update_cancel_ple_state(values)