from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = ['account.move', 'l10n.country.filter.mixin']
    _name = 'account.move'

    igv_withholding_indicator = fields.Boolean(
        string='Purchases IGV or Rent Withholding Indicator',
        help='If the field is activated, it automatically appears in the purchase record that the payment receipt is subject to IGV, Rent or both withholding inclusive'
    )
    inv_id = fields.Many2one(
        string='Proof of Payment',
        comodel_name='account.move',
        domain=[('state', 'not in', ['draft', 'cancel'])]
    )
    inv_type_document = fields.Many2one(
        comodel_name='l10n_latam.document.type',
        string='PLE Document Type',
        help='Document Type that supports the fiscal credit.'
    )
    inv_serie = fields.Char(
        string='Receipt Series',
        help='Series of the payment voucher or document that supports the fiscal credit.'
             'In the cases of the Single Customs Declaration (DUA) or the '
             'Simplified Import Declaration (DSI) the code of the Customs dependency shall be entered.'
    )
    inv_correlative = fields.Char(
        string='Receipt Correlative',
        help='Number of the payment voucher or document or order number of the physical or virtual form'
             ' where the payment of the tax is stated, in the case of the use of services provided by'
             ' non-domiciled or others, number of the DUA or DSI, which supports the fiscal credit.'
    )
    inv_year_dua_dsi = fields.Char(
        string='Year of Issuance DUA or DSI',
        size=4,
        help='Year of issuance of the DUA or DSI that supports the fiscal credit. Odoo validates that this field '
             'registers a number greater than 1981 and less than or equal to the year of the reported period'
    )
    inv_retention_igv = fields.Float(
        string='IGV Withholding Amount',
        digits=(12, 2),
        help='Amount of IGV Withholding'
    )
    is_nodomicilied = fields.Boolean(
        string='Non-Domiciled',
        compute='_compute_is_nodomicilied',
        store=True,
        readonly=False,
    )
    linkage_id = fields.Many2one(
        comodel_name='link.economic',
        string='Linkage',
        help='Link between the taxpayer and the resident abroad.'
             'Completed according to Table 27 of SUNAT Annex 2.'
    )
    hard_rent = fields.Float(
        string='Gross Income',
        digits=(12, 2)
    )
    deduccion_cost = fields.Float(
        string='Deduction/Cost',
        digits=(12, 2),
    )
    neto_rent = fields.Float(
        string='Net Income',
        digits=(12, 2)
    )
    retention_rate = fields.Float(
        string='Withholding Rate',
        digits=(3, 2),
    )
    tax_withheld = fields.Float(
        string='Tax Withheld',
        digits=(12, 2)
    )
    cdi = fields.Selection(
        string='CDI',
        selection=[
            ("00", "NONE"),
            ("01", "CANADA"),
            ("02", "CHILE"),
            ("03", "ANDEAN COMMUNITY OF NATIONS (CAN)"),
            ("04", "BRAZIL"),
            ("05", "MEXICO"),
            ("06", "SOUTH KOREA"),
            ("07", "SWISS CONFEDERATION"),
            ("08", "PORTUGAL"),
            ("09", "OTHERS")
        ],
        help='Conventions to avoid double taxation.'
             'This field is autocompleted with the field “Double Taxation Avoidance Convention Code”.'
             'Completed according to Table 25 of SUNAT Annex 2.'
    )
    exoneration_nodomicilied_id = fields.Many2one(
        comodel_name='exoneration.nodomicilied',
        string='Non-Domiciled Exoneration'
    )
    type_rent_id = fields.Many2one(
        comodel_name='type.rent',
        string='Rent Type'
    )
    taken_id = fields.Many2one(
        string='Service Rendered Provided',
        comodel_name='service.taken'
    )
    application_article = fields.Char(
        string='Application Art. 76°',
        help='Enter 1 if applicable, otherwise leave blank. '
             '(Application of the penultimate paragraph of Art. 76 of the Income Tax Law)'
    )

    types_goods_services_id = fields.Many2one(
        comodel_name='classification.services',
        string='Classification of Goods/Services Acquired'
    )

    @api.depends('company_id', 'partner_id')
    def _compute_is_nodomicilied(self):
        for obj in self:
            if obj.partner_id and obj.company_id.country_id == self.env.ref('base.pe'):
                if obj.partner_id.country_id and obj.partner_id.country_id == obj.company_id.country_id:
                    obj.is_nodomicilied = False
                elif not obj.partner_id.country_id:
                    obj.is_nodomicilied = False
                else:
                    obj.is_nodomicilied = True


    @api.model_create_multi
    def create(self, values):
        r = super(AccountMove, self).create(values)
        for move in r:
            if move.move_type in ['out_invoice', 'out_refund']:
                move.ple_state = '1'
            elif move.move_type in ['in_invoice', 'in_refund']:
                zero_taxes = 0
                for line in move.invoice_line_ids:
                    for tax in line.tax_ids:
                        if tax.amount == 0.00:
                            zero_taxes += 1

                if move.is_nodomicilied or zero_taxes == len(move.invoice_line_ids):
                    move.ple_state = '0'
                elif move.ple_date and move.invoice_date and move.invoice_date.month < move.ple_date.month or (
                        move.invoice_date and move.invoice_date.year < move.ple_date.year):
                    move.ple_state = '6'
                else:
                    move.ple_state = '1'
        return r

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type in ('form'):
            tags = [('field', 'is_nodomicilied'), ('field', 'bool_pay_invoice')]
            arch, view = self._tags_invisible_per_country(arch, view, view_type, tags, [self.env.ref('base.pe')])
        return arch, view

    @api.onchange('date')
    def onchange_ple_date_from_date(self):
        self.ple_date = self.date
        self.validation_ple_state()

    @api.onchange('invoice_date')
    def onchange_date_from_invoice_date(self):
        if self.invoice_date:
            self.date = self.invoice_date
            self.validation_ple_state()

    @api.onchange('invoice_line_ids')
    def onchange_invoice_line_ids_validation_ple(self):
        if self.invoice_line_ids:
            self.validation_ple_state()

    def validation_ple_state(self):
        taxes_diff = 0
        for line in self.invoice_line_ids:
            for tax in line.tax_ids:
                if tax.amount == 0.00:
                    taxes_diff += 1
        if self.is_nodomicilied or taxes_diff == len(self.invoice_line_ids):
            self.ple_state = '0'
        elif self.invoice_date and self.date:
            if self.invoice_date.month < self.date.month or self.invoice_date.year < self.date.year:
                self.ple_state = '6'
            else:
                self.ple_state = '1'
        else:
            self.ple_state = '1'

    @api.onchange('invoice_line_ids', 'l10n_latam_document_type_id')
    def nodomicilied_fields_update(self):

        fiscal_position_name = self.partner_id.property_account_position_id.name
        country_res = self.partner_id.country_id
        doc_type = self.l10n_latam_document_type_id
        ret_no_domi_30 = self.env['account.tax'].search([('name', '=', '30% RET. NO DOMICILIADO')], limit=1).id
        ret_no_domi_18 = self.env['account.tax'].search([('name', '=', '18% NO DOMICILIADO')], limit=1).id

        # --- First Case
        cond11 = country_res.code != "pe"
        cond12 = fiscal_position_name in ('NO DOMICILIADO SIN CDI', "NO DOMICILIADO CON CDI")
        cond14 = doc_type.code == '91'
        cond15 = False

        for line in self.invoice_line_ids:
            tax_ids = line.tax_ids.ids
            if ret_no_domi_30 in tax_ids or ret_no_domi_18 in tax_ids:
                cond15 = True
                break

        # --- Second Case
        cond21 = cond11
        cond22 = fiscal_position_name == "IMPORTACIONES"
        cond24 = cond14

        account_type_dict = dict(self.env['account.account']._fields['account_type']._description_selection(self.env))

        if cond11 and cond12 and self.is_nodomicilied and cond14 and cond15:

            # Monto de retencion de igv
            move_line_ret_igv = None
            for line in self.line_ids:
                if account_type_dict[line.account_id.account_type] == 'Activos Circulantes':
                    move_line_ret_igv = line
                    break

            self.inv_retention_igv = move_line_ret_igv.debit if move_line_ret_igv else 0.00

            # Renta bruta
            move_line_hard_rent = None
            for line in self.line_ids:
                if account_type_dict[line.account_id.account_type] == 'Por pagar':
                    move_line_hard_rent = line
                    break

            self.hard_rent = move_line_hard_rent.credit if move_line_hard_rent else 0.00

            # Renta neta
            self.neto_rent = self.hard_rent - self.deduccion_cost

            if fiscal_position_name == "NO DOMICILIADO SIN CDI":
                # Tasa de retención

                self.retention_rate = 0.00
                for line in self.invoice_line_ids:
                    if ret_no_domi_30 in line.tax_ids.ids:
                        self.retention_rate = 30.00
                        break

                # Impuesto Retenido
                move_line_ret = None
                for line in self.line_ids:
                    if account_type_dict[line.account_id.account_type] == 'Pasivos Circulantes' and line.account_id.code[:5] == '40174':
                        move_line_ret = line
                        break

                self.tax_withheld = move_line_ret.credit if move_line_ret else 0.00

            elif fiscal_position_name == "NO DOMICILIADO CON CDI":
                # Tasa de retención
                ret_nodom_tag_id = self.env['account.tax'].search([('name', '=', '30% RET. NO DOMICILIADO')],
                                                                  limit=1).id

                for line in self.invoice_line_ids:
                    if ret_nodom_tag_id in line.tax_ids.ids:
                        self.hard_rent = 0.00
                        self.neto_rent = 0.00
                        break

                self.retention_rate = 0.00

                # Impuesto Retenido
                self.tax_withheld = 0.00

        elif cond21 and cond22 and self.is_nodomicilied and cond24:
            move_line_hard_rent = None
            for line in self.line_ids:
                if account_type_dict[line.account_id.account_type] == 'Por pagar':
                    move_line_hard_rent = line
                    break

            self.hard_rent = move_line_hard_rent.credit if move_line_hard_rent else 0.00
            self.neto_rent = self.hard_rent - self.deduccion_cost
            self.inv_retention_igv = 0.00
            self.retention_rate = 0.00
            self.tax_withheld = 0.00

        else:
            self.inv_retention_igv = 0.00
            self.hard_rent = 0.00
            self.neto_rent = 0.00
            self.retention_rate = 0.00
            self.tax_withheld = 0.00

