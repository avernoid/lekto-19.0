from odoo import fields, models, api


class ModelSunatCatalog(models.AbstractModel):
    _name = 'model.sunat.catalog'
    _description = 'SUNAT Catalog Model'

    name = fields.Char(
        string='Name',
        compute='compute_name',
        help='Computed name combining code and description.'
    )
    code = fields.Char(
        string='Code',
        required=True,
        help='Unique code defined by SUNAT.'
    )
    description = fields.Char(
        string='Description',
        required=True,
        help='Official description of the code.'
    )

    @api.depends('code', 'description')
    def compute_name(self):
        for rec in self:
            rec.name = "[%s] %s" % (rec.code or '', rec.description or '')


class ChargeDiscountCodes(models.Model):
    _name = 'charge.discount.codes'
    _description = '[53] Charge or Discount Codes'
    _inherit = 'model.sunat.catalog'


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_pe_charge_discount_id = fields.Many2one(
        comodel_name='charge.discount.codes',
        string='Charge/Discount Code',
        help='Code from SUNAT Catalog 53 to be used for charges or discounts applied to this product.'
    )


class ClassificationServices(models.Model):
    _name = 'classification.services'
    _description = '[30] Goods and Services Classification'

    code = fields.Char(
        string='Code',
        required=True,
        help='Classification code according to SUNAT Catalog 30.'
    )

    description = fields.Char(
        string='Description',
        required=True,
        help='Description of the good or service classification.'
    )

    @api.depends('code', 'description')
    def _compute_display_name(self):
        for services in self:
            services.display_name = f"{services.code} {services.description}"

class PaymentMethodsCodes(models.Model):
    _name = 'payment.methods.codes'
    _description = '[59] Payment Methods Codes'
    _rec_name = 'description'

    code = fields.Char(
        string='Code',
        required=True,
        help='Payment method code from SUNAT Catalog 59.'
    )

    description = fields.Char(
        string='Description',
        required=True,
        help='Description of the payment method.'
    )
